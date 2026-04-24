from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from core.database import get_session
from app.modules.producto.schemas import (
    ProductoCreate, ProductoPublic, ProductoUpdate, ProductoList,
)
from app.modules.producto.service import ProductoService

router = APIRouter(prefix="/productos", tags=["Productos"])


def get_producto_service(session: Session = Depends(get_session)) -> ProductoService:
    """Factory de dependencia: inyecta el servicio con su Session."""
    return ProductoService(session)


# ── Endpoints ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=ProductoPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un producto",
)
def crear_producto(
    data: ProductoCreate,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoPublic:
    return svc.crear(data)


@router.get(
    "/",
    response_model=ProductoList,
    status_code=status.HTTP_200_OK,
    summary="Listar productos activos (paginado)",
)
def listar_productos(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoList:
    return svc.listar_activos(offset=offset, limit=limit)


@router.get(
    "/{id}",
    response_model=ProductoPublic,
    status_code=status.HTTP_200_OK,
    summary="Obtener producto por ID",
)
def obtener_producto(
    id: int,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoPublic:
    return svc.obtener_por_id(id)


@router.patch(
    "/{id}",
    response_model=ProductoPublic,
    status_code=status.HTTP_200_OK,
    summary="Actualización parcial de producto",
)
def actualizar_producto(
    id: int,
    data: ProductoUpdate,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoPublic:
    return svc.actualizar(id, data)


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Soft delete de producto",
)
def eliminar_producto(
    id: int,
    svc: ProductoService = Depends(get_producto_service),
):
    return svc.eliminar_logicamente(id)