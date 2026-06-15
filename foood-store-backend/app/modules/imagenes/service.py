from fastapi import HTTPException, status
from sqlmodel import Session, select
from typing import Optional
from fastapi import UploadFile
import cloudinary
import cloudinary.uploader
import cloudinary.api

from core.config import settings
from .unit_of_work import ImagenUnitOfWork
from .models import Imagen
from .schemas import ImagenPublic, ImagenList
from app.modules.usuario.models import Usuario  # noqa: F401 — registra el modelo para FK


class ImagenService:
    def __init__(self, session: Session):
        self.session = session
        # Configurar Cloudinary con las credenciales del settings
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
        )

    # ------------------------------------------------------------------
    async def subir_imagen(
        self,
        file: UploadFile,
        folder: str = "productos",
        nombre_archivo: Optional[str] = None,
        subido_por_id: int = 0,
    ) -> ImagenPublic:
        """Sube una imagen a Cloudinary y persiste el registro en la BD."""
        # Leer contenido del archivo
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo está vacío.",
            )
        if len(contents) > settings.CLOUDINARY_MAX_FILE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El archivo supera el límite de {settings.CLOUDINARY_MAX_FILE_MB} MB.",
            )

        # Determinar el public_id base
        original_name = nombre_archivo or file.filename or "img"
        safe_name = "".join(c for c in original_name if c.isalnum() or c in "._-").rstrip()
        # Carpeta completa en Cloudinary: foodstore/productos
        cloud_folder = f"{settings.CLOUDINARY_FOLDER}/{folder}"

        # Subir a Cloudinary
        try:
            result = cloudinary.uploader.upload(
                contents,
                folder=cloud_folder,
                public_id=safe_name,
                resource_type="image",
                overwrite=True,
                transformation=[
                    {"width": 800, "height": 800, "crop": "limit"},
                    {"quality": "auto", "fetch_format": "auto"},
                ],
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al subir a Cloudinary: {str(e)}",
            )

        # Extraer datos de la respuesta de Cloudinary
        public_id: str = result.get("public_id", "")
        url: str = result.get("url", "")
        secure_url: Optional[str] = result.get("secure_url", None)
        formato: str = result.get("format", file.content_type or "unknown")
        ancho: int = result.get("width", 0)
        alto: int = result.get("height", 0)
        bytes_size: int = result.get("bytes", 0)
        recurso_tipo: str = result.get("resource_type", "image")

        # Persistir en la BD
        with ImagenUnitOfWork(self.session) as uow:
            # Verificar que no exista ya (por public_id único)
            existing = uow.imagenes.get_by_public_id(public_id)
            if existing:
                # Actualizar si ya existe (overwrite en Cloudinary)
                existing.url = url
                existing.secure_url = secure_url
                existing.formato = formato
                existing.ancho = ancho
                existing.alto = alto
                existing.bytes = bytes_size
                existing.nombre_archivo = nombre_archivo
                uow.imagenes.session.add(existing)
                uow.imagenes.session.flush()
                img = existing
            else:
                img = Imagen(
                    public_id=public_id,
                    url=url,
                    secure_url=secure_url,
                    formato=formato,
                    ancho=ancho,
                    alto=alto,
                    bytes=bytes_size,
                    folder=folder,
                    recurso_tipo=recurso_tipo,
                    subido_por_id=subido_por_id,
                    nombre_archivo=nombre_archivo,
                )
                uow.imagenes.session.add(img)
                uow.imagenes.session.flush()

        return ImagenPublic.model_validate(img)

    # ------------------------------------------------------------------
    def listar_imagenes(
        self,
        offset: int = 0,
        limit: int = 12,
        q: Optional[str] = None,
        folder: Optional[str] = None,
    ) -> ImagenList:
        """Lista imágenes con búsqueda opcional por nombre y filtro por carpeta."""
        with ImagenUnitOfWork(self.session) as uow:
            if q:
                imagenes = uow.imagenes.buscar(q, offset, limit, folder)
                total = uow.imagenes.contar_buscar(q, folder)
            else:
                imagenes = uow.imagenes.get_todas(offset, limit, folder=folder, incluir_eliminadas=False)
                total = uow.imagenes.contar_todas(folder=folder, incluir_eliminadas=False)
            return ImagenList(
                data=[ImagenPublic.model_validate(i) for i in imagenes],
                total=total,
            )

    # ------------------------------------------------------------------
    def obtener_imagen(self, imagen_id: int) -> ImagenPublic:
        """Obtiene una imagen por ID."""
        with ImagenUnitOfWork(self.session) as uow:
            img = uow.imagenes.get_by_id(imagen_id)
            if not img or img.eliminado_en is not None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Imagen no encontrada.",
                )
            return ImagenPublic.model_validate(img)

    # ------------------------------------------------------------------
    def sincronizar_con_cloudinary(
        self,
        cloud_folder: str = "productos",
        admin_user_id: int = 1,
    ) -> dict:
        """
        Sincroniza la BD local con los recursos reales de Cloudinary.
        - Crea filas en BD para imágenes nuevas en Cloudinary.
        - Marca como eliminadas las filas huérfanas (ya no existen en Cloudinary).
        - Excluye recursos con 'samples/' en el public_id (imágenes demo de Cloudinary).
        """
        from datetime import datetime, timezone
        full_cloud_folder = f"{settings.CLOUDINARY_FOLDER}/{cloud_folder}"

        try:
            result = cloudinary.api.resources(
                folder=full_cloud_folder,
                type="upload",
                resource_type="image",
                max_results=500,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al consultar Cloudinary: {str(e)}",
            )

        resources: list = result.get("resources", [])
        # Filtrar: excluir todo lo que tenga "samples/" en el public_id
        resources = [r for r in resources if "samples/" not in r.get("public_id", "")]
        cloud_public_ids: set = {r.get("public_id", "") for r in resources}

        creados = 0
        eliminados = 0
        total_en_cloud = len(cloud_public_ids)
        total_en_db = 0

        with ImagenUnitOfWork(self.session) as uow:
            all_db_imgs = uow.imagenes.session.exec(
                select(Imagen)
            ).all()
            db_public_ids: dict = {img.public_id: img for img in all_db_imgs}
            total_en_db = len(db_public_ids)

            for resource in resources:
                public_id: str = resource.get("public_id", "")
                if not public_id or public_id in db_public_ids:
                    continue

                img = Imagen(
                    public_id=public_id,
                    url=resource.get("url", ""),
                    secure_url=resource.get("secure_url"),
                    formato=resource.get("format", "unknown"),
                    ancho=resource.get("width", 0),
                    alto=resource.get("height", 0),
                    bytes=resource.get("bytes", 0),
                    folder=cloud_folder,
                    recurso_tipo="image",
                    subido_por_id=admin_user_id,
                    nombre_archivo=None,
                )
                uow.imagenes.session.add(img)
                creados += 1

            uow.imagenes.session.flush()

            for public_id, img in db_public_ids.items():
                # Eliminar si: ya no está en cloud O si tiene "samples/" en el public_id
                is_sample = "samples/" in public_id
                not_in_cloud = public_id not in cloud_public_ids
                if (is_sample or not_in_cloud) and img.eliminado_en is None:
                    img.eliminado_en = datetime.now(timezone.utc)
                    uow.imagenes.session.add(img)
                    eliminados += 1

            uow.imagenes.session.flush()

        return {
            "total_en_cloud": total_en_cloud,
            "total_en_db": total_en_db,
            "creados": creados,
            "eliminados": eliminados,
            "carpeta": cloud_folder,
        }

    # ------------------------------------------------------------------
    def eliminar_imagen(self, imagen_id: int) -> None:
        """Soft-delete en BD + eliminación en Cloudinary + limpieza de referencias en productos."""
        import cloudinary.uploader
        with ImagenUnitOfWork(self.session) as uow:
            img = uow.imagenes.get_by_id(imagen_id)
            if not img or img.eliminado_en is not None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Imagen no encontrada.",
                )
            # Guardar URLs antes de eliminar para limpiar productos
            url_to_clear = img.secure_url or img.url

            # 1) Eliminar de Cloudinary
            try:
                cloudinary.uploader.destroy(img.public_id, invalidate=True)
            except Exception:
                # Si falla Cloudinary, igual seguimos (soft-delete en BD)
                pass

            # 2) Limpiar referencias en productos (hardening)
            if url_to_clear:
                from app.modules.catalogo.producto.models import Producto
                uow.session.exec(
                    Producto.__table__.update()
                    .where(Producto.imagen_url == url_to_clear)
                    .values(imagen_url=None)
                )
                uow.session.flush()

            # 3) Soft-delete en BD
            uow.imagenes.soft_delete(img)
