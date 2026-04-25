from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from core.database import get_session
from app.modules.categoria.schemas import (
    CategoriaCreate, CategoriaPublic, CategoriaUpdate, CategoriaList,
    CategoriaWithProductos, CategoriaConProductosList,
)
from app.modules.categoria.service import CategoriaService

router = APIRouter(prefix="/categorias", tags=["Categorías"])


def get_categoria_service(session: Session = Depends(get_session)) -> CategoriaService:
    """Factory de dependencia: inyecta el servicio con su Session."""
    return CategoriaService(session)


# ── Endpoints ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=CategoriaPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una categoría",
)
def crear_categoria(
    data: CategoriaCreate,
    svc: CategoriaService = Depends(get_categoria_service),
) -> CategoriaPublic:
    return svc.crear(data)


@router.get(
    "/",
    response_model=CategoriaList,
    status_code=status.HTTP_200_OK,
    summary="Listar categorías activas (paginado)",
)
def listar_categorias(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    svc: CategoriaService = Depends(get_categoria_service),
) -> CategoriaList:
    return svc.listar_activas(offset=offset, limit=limit)


# IMPORTANTE: declarar /con-productos ANTES que /{id} para que FastAPI no intente
# convertir la cadena literal "con-productos" como un parámetro entero.
@router.get(
    "/con-productos",
    response_model=CategoriaConProductosList,
    status_code=status.HTTP_200_OK,
    summary="Listar categorías activas con sus productos embebidos (paginado)",
)
def listar_categorias_con_productos(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    svc: CategoriaService = Depends(get_categoria_service),
) -> CategoriaConProductosList:
    return svc.listar_con_productos(offset=offset, limit=limit)


@router.get(
    "/{id}",
    response_model=CategoriaPublic,
    status_code=status.HTTP_200_OK,
    summary="Obtener categoría por ID",
)
def obtener_categoria(
    id: int,
    svc: CategoriaService = Depends(get_categoria_service),
) -> CategoriaPublic:
    return svc.obtener_por_id(id)


@router.get(
    "/{id}/productos",
    response_model=CategoriaWithProductos,
    status_code=status.HTTP_200_OK,
    summary="Obtener categoría con sus productos embebidos",
)
def obtener_categoria_con_productos(
    id: int,
    svc: CategoriaService = Depends(get_categoria_service),
) -> CategoriaWithProductos:
    return svc.get_with_productos(id)


@router.get(
    "/{id}/subcategorias",
    response_model=CategoriaList,
    status_code=status.HTTP_200_OK,
    summary="Listar subcategorías directas de una categoría",
)
def listar_subcategorias(
    id: int,
    svc: CategoriaService = Depends(get_categoria_service),
) -> CategoriaList:
    return svc.listar_subcategorias(id)


@router.patch(
    "/{id}",
    response_model=CategoriaPublic,
    status_code=status.HTTP_200_OK,
    summary="Actualización parcial de categoría",
)
def actualizar_categoria(
    id: int,
    data: CategoriaUpdate,
    svc: CategoriaService = Depends(get_categoria_service),
) -> CategoriaPublic:
    return svc.actualizar(id, data)


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Soft delete de categoría",
)
def eliminar_categoria(
    id: int,
    svc: CategoriaService = Depends(get_categoria_service),
):
    return svc.eliminar_logicamente(id)


@router.post(
    "/{id}/restaurar",
    response_model=CategoriaPublic,
    status_code=status.HTTP_200_OK,
    summary="Restaurar categoría eliminada (revertir soft-delete)",
)
def restaurar_categoria(
    id: int,
    svc: CategoriaService = Depends(get_categoria_service),
) -> CategoriaPublic:
    return svc.restaurar(id)