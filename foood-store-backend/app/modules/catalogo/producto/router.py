from fastapi import APIRouter, Depends, status
from sqlmodel import Session
from typing import List, Optional

from core.database import get_session
from core.security import RoleChecker
from .schemas import ProductoCreate, ProductoUpdate, ProductoPublic
from .service import ProductoService

router = APIRouter(prefix="/productos", tags=["Catálogo - Productos"])

_solo_admin = Depends(RoleChecker(["ADMIN"]))
_admin_o_stock = Depends(RoleChecker(["ADMIN", "GESTOR_STOCK"]))


def get_service(session: Session = Depends(get_session)) -> ProductoService:
    return ProductoService(session)


@router.post("", response_model=ProductoPublic, status_code=status.HTTP_201_CREATED,
             dependencies=[_admin_o_stock])
def crear_producto(data: ProductoCreate, svc: ProductoService = Depends(get_service)):
    """
    Crea un plato final con escandallo automático. ADMIN o GESTOR_STOCK.
    """
    return svc.crear_producto(data)


@router.get("", response_model=List[ProductoPublic])
def listar_productos(
    categoria_id: Optional[int] = None,
    activo: Optional[bool] = None,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
    incluir_eliminados: bool = False,
    svc: ProductoService = Depends(get_service),
):
    """
    Listado con filtros opcionales.
    - `incluir_eliminados=true`: devuelve activos + eliminados (para panel admin).
    """
    return svc.listar_productos(
        categoria_id=categoria_id,
        activo=activo,
        q=q,
        skip=skip,
        limit=limit,
        incluir_eliminados=incluir_eliminados,
    )


@router.get("/{producto_id}", response_model=ProductoPublic)
def obtener_producto(producto_id: int, svc: ProductoService = Depends(get_service)):
    """Obtiene un producto por ID con su receta completa."""
    return svc.obtener_producto(producto_id)


@router.patch("/{producto_id}", response_model=ProductoPublic, dependencies=[_admin_o_stock])
def actualizar_producto(
    producto_id: int,
    data: ProductoUpdate,
    svc: ProductoService = Depends(get_service),
):
    """
    Actualiza un producto. Recalcula escandallo si se envía nueva receta. ADMIN o GESTOR_STOCK.
    """
    return svc.actualizar_producto(producto_id, data)


@router.patch("/{producto_id}/disponibilidad", response_model=ProductoPublic,
              dependencies=[_admin_o_stock])
def toggle_disponibilidad(
    producto_id: int,
    activo: bool,
    svc: ProductoService = Depends(get_service),
):
    """Activa o desactiva el estado activo del producto. ADMIN o GESTOR_STOCK."""
    return svc.toggle_disponibilidad(producto_id, activo)


@router.patch("/{producto_id}/reactivar", response_model=ProductoPublic,
              dependencies=[_admin_o_stock])
def reactivar_producto(
    producto_id: int, svc: ProductoService = Depends(get_service)
):
    """Restaura un producto dado de baja (limpia eliminado_en). ADMIN o GESTOR_STOCK."""
    return svc.reactivar_producto(producto_id)


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[_admin_o_stock])
def eliminar_producto(
    producto_id: int, svc: ProductoService = Depends(get_service)
):
    """Soft-delete: oculta el producto del catálogo. ADMIN o GESTOR_STOCK."""
    svc.eliminar_producto(producto_id)
