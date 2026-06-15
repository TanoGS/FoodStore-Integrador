from sqlmodel import Session, select, func
from typing import List, Optional
from core.repository import BaseRepository
from .models import Imagen


class ImagenRepository(BaseRepository[Imagen]):
    def __init__(self, session: Session):
        super().__init__(session, Imagen)

    def get_by_public_id(self, public_id: str) -> Optional[Imagen]:
        """Busca una imagen activa por su public_id de Cloudinary."""
        return self.session.exec(
            select(Imagen).where(
                Imagen.public_id == public_id,
                Imagen.eliminado_en == None,  # noqa: E711
            )
        ).first()

    def get_activas(self, offset: int = 0, limit: int = 50) -> List[Imagen]:
        """Trae todas las imágenes activas (sin filtro de usuario)."""
        return list(self.session.exec(
            select(Imagen)
            .where(Imagen.eliminado_en == None)  # noqa: E711
            .order_by(Imagen.creado_en.desc())
            .offset(offset)
            .limit(limit)
        ).all())

    def get_todas(
        self,
        offset: int = 0,
        limit: int = 50,
        folder: Optional[str] = None,
        incluir_eliminadas: bool = False,
    ) -> List[Imagen]:
        """Trae imágenes con opción de incluir eliminadas y filtro por carpeta."""
        query = select(Imagen)
        if not incluir_eliminadas:
            query = query.where(Imagen.eliminado_en == None)  # noqa: E711
        if folder:
            query = query.where(Imagen.folder == folder)
        return list(self.session.exec(
            query.order_by(Imagen.creado_en.desc())
            .offset(offset)
            .limit(limit)
        ).all())

    def contar_todas(
        self,
        folder: Optional[str] = None,
        incluir_eliminadas: bool = False,
    ) -> int:
        """Cuenta imágenes activas o todas, con filtro opcional por carpeta."""
        query = select(func.count(Imagen.id))
        if not incluir_eliminadas:
            query = query.where(Imagen.eliminado_en == None)  # noqa: E711
        if folder:
            query = query.where(Imagen.folder == folder)
        return self.session.exec(query).one()

    def buscar(
        self,
        q: str,
        offset: int = 0,
        limit: int = 12,
        folder: Optional[str] = None,
    ) -> List[Imagen]:
        """Busca imágenes por nombre de archivo (case-insensitive)."""
        query = select(Imagen).where(
            Imagen.eliminado_en == None,  # noqa: E711
        )
        # Búsqueda case-insensitive en nombre_archivo
        query = query.where(Imagen.nombre_archivo.ilike(f"%{q}%"))
        if folder:
            query = query.where(Imagen.folder == folder)
        return list(self.session.exec(
            query.order_by(Imagen.creado_en.desc())
            .offset(offset)
            .limit(limit)
        ).all())

    def contar_buscar(
        self,
        q: str,
        folder: Optional[str] = None,
    ) -> int:
        """Cuenta resultados de búsqueda."""
        query = select(func.count(Imagen.id)).where(
            Imagen.eliminado_en == None,  # noqa: E711
            Imagen.nombre_archivo.ilike(f"%{q}%"),
        )
        if folder:
            query = query.where(Imagen.folder == folder)
        return self.session.exec(query).one()

    def soft_delete(self, imagen: Imagen) -> None:
        """Marca una imagen como eliminada (soft-delete)."""
        from datetime import datetime, timezone
        imagen.eliminado_en = datetime.now(timezone.utc)
        self.session.add(imagen)
        self.session.flush()
