from fastapi import APIRouter, Depends, status
from sqlmodel import Session
from typing import List, Optional

from core.database import get_session
from core.security import RoleChecker
from .schemas import CategoriaCreate, CategoriaUpdate, CategoriaPublic
from .service import CategoriaService

router = APIRouter(prefix="/categorias", tags=["Catálogo - Categorías"])

_solo_admin = Depends(RoleChecker(["ADMIN"]))
_admin_o_stock = Depends(RoleChecker(["ADMIN", "GESTOR_STOCK"]))


def get_service(session: Session = Depends(get_session)) -> CategoriaService:
    return CategoriaService(session)


@router.post("", response_model=CategoriaPublic, status_code=status.HTTP_201_CREATED,
             dependencies=[_admin_o_stock])
def crear_categoria(data: CategoriaCreate, svc: CategoriaService = Depends(get_service)):
    """Crea una nueva sección para el menú. ADMIN o GESTOR_STOCK."""
    return svc.crear_categoria(data)


@router.get("", response_model=List[CategoriaPublic])
def listar_categorias(
    parent_id: Optional[int] = None,
    solo_raiz: bool = True,
    skip: int = 0,
    limit: int = 200,
    incluir_eliminados: bool = False,
    svc: CategoriaService = Depends(get_service),
):
    """
    Listado de categorías.
    - Sin parámetros: categorías raíz con `solo_raiz=true`.
    - `parent_id=X`: hijos directos de la categoría X.
    - `solo_raiz=false`: todas las categorías activas.
    - `incluir_eliminados=true`: devuelve activas + eliminadas (para panel admin).
    """
    return svc.listar_categorias(
        parent_id=parent_id,
        solo_raiz=solo_raiz,
        skip=skip,
        limit=limit,
        incluir_eliminados=incluir_eliminados,
    )


@router.get("/{categoria_id}", response_model=CategoriaPublic)
def obtener_categoria(categoria_id: int, svc: CategoriaService = Depends(get_service)):
    """Obtiene una categoría por ID con sus subcategorías directas."""
    return svc.obtener_categoria(categoria_id)


@router.patch("/{categoria_id}", response_model=CategoriaPublic, dependencies=[_admin_o_stock])
def actualizar_categoria(
    categoria_id: int,
    data: CategoriaUpdate,
    svc: CategoriaService = Depends(get_service),
):
    """Actualiza los campos enviados de una categoría. ADMIN o GESTOR_STOCK."""
    return svc.actualizar_categoria(categoria_id, data)


@router.patch("/{categoria_id}/visibilidad", response_model=CategoriaPublic,
              dependencies=[_admin_o_stock])
def toggle_visibilidad(
    categoria_id: int,
    activo: bool,
    svc: CategoriaService = Depends(get_service),
):
    """Activa o desactiva una categoría. ADMIN o GESTOR_STOCK."""
    return svc.actualizar_categoria(categoria_id, CategoriaUpdate(activo=activo))


@router.patch("/{categoria_id}/reactivar", response_model=CategoriaPublic,
              dependencies=[_admin_o_stock])
def reactivar_categoria(
    categoria_id: int, svc: CategoriaService = Depends(get_service)
):
    """Reactiva una categoría con soft-delete. Falla con 409 si su padre está eliminado. ADMIN o GESTOR_STOCK."""
    return svc.reactivar_categoria(categoria_id)


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[_admin_o_stock])
def eliminar_categoria(
    categoria_id: int, svc: CategoriaService = Depends(get_service)
):
    """Soft-delete con validación: falla con 409 si tiene hijos o productos activos. ADMIN o GESTOR_STOCK."""
    svc.eliminar_categoria(categoria_id)
