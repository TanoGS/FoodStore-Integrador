"""
Módulo: app/modules/productos/router.py
=======================================

Endpoints HTTP de Productos (refactorizado al patrón del modelo:
Depends(get_service) en vez de Depends(get_uow)).
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_user, require_role
from app.modules.productos.schemas import (
    ProductoCreate,
    ProductoList,
    ProductoPublic,
    ProductoUpdate,
)
from app.modules.productos.service import ProductoService
from app.modules.usuarios.schemas import UserPublic


# ---------------------------------------------------------------------------
# FACTORY: get_producto_service
# ---------------------------------------------------------------------------
def get_producto_service(
    session: Session = Depends(get_session),
) -> ProductoService:
    """Inyecta la session en el Service de Productos."""
    return ProductoService(session=session)


router = APIRouter(tags=["productos"])


# ===========================================================================
# POST /productos/
# ===========================================================================
@router.post(
    "/",
    response_model=ProductoPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un producto",
    description="Crea un producto nuevo. Requiere estar autenticado.",
)
def create_producto(
    payload: ProductoCreate,
    svc: ProductoService = Depends(get_producto_service),
    _current: UserPublic = Depends(get_current_user),
) -> ProductoPublic:
    """Crea un producto. Cualquier usuario autenticado puede crear."""
    return svc.create(payload)


# ===========================================================================
# GET /productos/ — búsqueda paginada con filtros
# ===========================================================================
@router.get(
    "/",
    response_model=ProductoList,
    summary="Buscar/listar productos",
    description=(
        "Lista productos con paginación y filtros opcionales: nombre "
        "(parcial, case-insensitive), categoría, rango de precio."
    ),
)
def search_productos(
    nombre: Optional[str] = Query(default=None, description="Filtro parcial por nombre."),
    categoria: Optional[str] = Query(default=None, description="Filtro exacto por categoría."),
    min_precio: Optional[float] = Query(default=None, ge=0, description="Precio mínimo."),
    max_precio: Optional[float] = Query(default=None, ge=0, description="Precio máximo."),
    skip: int = Query(default=0, ge=0, description="Offset de paginación."),
    limit: int = Query(default=100, ge=1, le=500, description="Tamaño de página (max 500)."),
    only_active: bool = Query(default=True, description="Si True, solo productos activos."),
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoList:
    """
    Búsqueda con query params. Todos los filtros son opcionales.

    Ejemplo: GET /productos/?categoria=tecnologia&min_precio=10&max_precio=100&limit=20
    """
    return svc.search(
        nombre=nombre,
        categoria=categoria,
        min_precio=min_precio,
        max_precio=max_precio,
        skip=skip,
        limit=limit,
        only_active=only_active,
    )


# ===========================================================================
# GET /productos/{producto_id}
# ===========================================================================
@router.get(
    "/{producto_id}",
    response_model=ProductoPublic,
    summary="Obtener un producto por ID",
)
def get_producto(
    producto_id: int,
    include_inactive: bool = Query(default=False, description="Si True, incluye productos inactivos."),
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoPublic:
    return svc.get_by_id(producto_id, include_inactive)


# ===========================================================================
# PATCH /productos/{producto_id}
# ===========================================================================
@router.patch(
    "/{producto_id}",
    response_model=ProductoPublic,
    summary="Actualizar un producto (parcial)",
)
def update_producto(
    producto_id: int,
    payload: ProductoUpdate,
    svc: ProductoService = Depends(get_producto_service),
    current_user: UserPublic = Depends(get_current_user),
) -> ProductoPublic:
    is_admin = current_user.rol == "admin"
    return svc.update(producto_id, payload, is_admin)


# ===========================================================================
# POST /productos/admin/{producto_id}/descontinuar
# POST /productos/admin/{producto_id}/reactivar
# ===========================================================================
@router.post(
    "/admin/{producto_id}/descontinuar",
    response_model=ProductoPublic,
    summary="Descontinuar un producto (solo admin)",
)
def discontinue_producto(
    producto_id: int,
    svc: ProductoService = Depends(get_producto_service),
    _admin: UserPublic = Depends(require_role(["admin"])),
    current_user: UserPublic = Depends(get_current_user),
) -> ProductoPublic:
    """Soft delete. Solo admins."""
    return svc.set_active(producto_id, is_active=False, is_admin=current_user.rol == "admin")


@router.post(
    "/admin/{producto_id}/reactivar",
    response_model=ProductoPublic,
    summary="Reactivar un producto (solo admin)",
)
def reactivate_producto(
    producto_id: int,
    svc: ProductoService = Depends(get_producto_service),
    _admin: UserPublic = Depends(require_role(["admin"])),
    current_user: UserPublic = Depends(get_current_user),
) -> ProductoPublic:
    """Reactivar un producto descontinuado. Solo admins."""
    return svc.set_active(producto_id, is_active=True, is_admin=current_user.rol == "admin")
