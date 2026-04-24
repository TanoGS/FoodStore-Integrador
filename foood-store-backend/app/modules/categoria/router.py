from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from core.database import get_session
from app.modules.categoria.schemas import (
    CategoriaCreate, CategoriaPublic, CategoriaUpdate, CategoriaList,
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