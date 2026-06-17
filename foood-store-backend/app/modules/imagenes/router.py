from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlmodel import Session

from core.database import get_session
from core.security import get_current_user_token, RoleChecker, TokenData
from .schemas import ImagenPublic, ImagenList
from .service import ImagenService

router = APIRouter(prefix="/imagenes", tags=["Imágenes"])

_admin_y_stock = Depends(RoleChecker(["ADMIN", "GESTOR_STOCK"]))


def get_svc(session: Session = Depends(get_session)) -> ImagenService:
    return ImagenService(session)


@router.post(
    "/upload",
    response_model=ImagenPublic,
    dependencies=[_admin_y_stock],
)
async def subir_imagen(
    file: UploadFile = File(..., description="Archivo de imagen (JPG, PNG, WEBP)"),
    folder: str = Form("productos", description="Carpeta en Cloudinary (ej: productos)"),
    nombre_archivo: str | None = Form(None, description="Nombre amigable para la imagen"),
    current_user: TokenData = Depends(get_current_user_token),
    svc: ImagenService = Depends(get_svc),
):
    """Sube una imagen a Cloudinary y la persiste en la base de datos."""
    return await svc.subir_imagen(
        file=file,
        folder=folder,
        nombre_archivo=nombre_archivo,
        subido_por_id=int(current_user.id),
    )


@router.get(
    "",
    response_model=ImagenList,
    dependencies=[_admin_y_stock],
)
def listar_imagenes(
    offset: int = Query(0, ge=0),
    limit: int = Query(12, ge=1, le=50),
    q: str | None = Query(None, description="Búsqueda por nombre de archivo"),
    folder: str | None = Query(None, description="Filtrar por carpeta "),
    svc: ImagenService = Depends(get_svc),
):
    return svc.listar_imagenes(offset=offset, limit=limit, q=q, folder=folder)


@router.get(
    "/{imagen_id}",
    response_model=ImagenPublic,
    dependencies=[_admin_y_stock],
)
def obtener_imagen(
    imagen_id: int,
    svc: ImagenService = Depends(get_svc),
):
    """
    Obtiene una imagen por su ID.
    - ADMIN y GESTOR_STOCK tienen acceso.
    """
    return svc.obtener_imagen(imagen_id)


@router.post(
    "/sincronizar",
    dependencies=[_admin_y_stock],
)
def sincronizar_imagenes(
    folder: str = Query("productos", description="Carpeta a sincronizar (ej: productos)"),
    current_user: TokenData = Depends(get_current_user_token),
    svc: ImagenService = Depends(get_svc),
):
    """
    Sincroniza la tabla local de imágenes con los recursos reales en Cloudinary.
    - Crea filas para imágenes nuevas en Cloudinary.
    - Marca como eliminadas las filas huérfanas.
    """
    return svc.sincronizar_con_cloudinary(cloud_folder=folder, admin_user_id=int(current_user.id))


@router.delete(
    "/{imagen_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_admin_y_stock],
)
def eliminar_imagen(
    imagen_id: int,
    svc: ImagenService = Depends(get_svc),
):
    svc.eliminar_imagen(imagen_id)


@router.delete(
    "/cloudinary/{public_id:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_admin_y_stock],
    summary="Eliminar imagen de Cloudinary por public_id",
)
def eliminar_imagen_por_public_id(
    public_id: str,
    svc: ImagenService = Depends(get_svc),
):
    """
    Elimina una imagen de Cloudinary usando su `public_id` (spec sección 5.5).
    También borra el registro en BD si existe. ADMIN o GESTOR_STOCK.
    """
    svc.eliminar_imagen_por_public_id(public_id)
