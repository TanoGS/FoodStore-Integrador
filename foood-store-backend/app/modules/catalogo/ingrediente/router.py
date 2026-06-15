from fastapi import APIRouter, Depends, status
from sqlmodel import Session
from typing import List

from core.database import get_session
from core.security import RoleChecker
from .schemas import (
    IngredienteCreate,
    IngredienteUpdate,
    IngredientePublic,
)
from .service import IngredienteService

router = APIRouter(prefix="/ingredientes", tags=["Inventario - Depósito"])

_solo_admin = Depends(RoleChecker(["ADMIN"]))
_admin_o_stock = Depends(RoleChecker(["ADMIN", "GESTOR_STOCK"]))


def get_service(session: Session = Depends(get_session)) -> IngredienteService:
    return IngredienteService(session)


# ==============================================================================
# Ingredientes
# ==============================================================================
@router.post(
    "",
    response_model=IngredientePublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin_o_stock],
)
def crear_ingrediente(
    data: IngredienteCreate, svc: IngredienteService = Depends(get_service)
):
    """Da de alta un insumo con su costo y unidad de medida. ADMIN o GESTOR_STOCK."""
    return svc.crear_ingrediente(data)


@router.get("", response_model=List[IngredientePublic])
def listar_ingredientes(
    offset: int = 0,
    limit: int = 200,
    incluir_eliminados: bool = False,
    svc: IngredienteService = Depends(get_service),
):
    """Lista la materia prima. Con incluir_eliminados=true devuelve también los dados de baja."""
    return svc.listar_ingredientes(offset, limit, incluir_eliminados)


@router.get("/{ingrediente_id}", response_model=IngredientePublic)
def obtener_ingrediente(
    ingrediente_id: int, svc: IngredienteService = Depends(get_service)
):
    return svc.obtener_ingrediente(ingrediente_id)


@router.patch("/{ingrediente_id}", response_model=IngredientePublic,
              dependencies=[_admin_o_stock])
def actualizar_ingrediente(
    ingrediente_id: int,
    data: IngredienteUpdate,
    svc: IngredienteService = Depends(get_service),
):
    """Actualiza un ingrediente. ADMIN o GESTOR_STOCK."""
    return svc.actualizar_ingrediente(ingrediente_id, data)


@router.patch("/{ingrediente_id}/reactivar", response_model=IngredientePublic,
              dependencies=[_admin_o_stock])
def reactivar_ingrediente(
    ingrediente_id: int, svc: IngredienteService = Depends(get_service)
):
    """Restaura un ingrediente dado de baja (limpia eliminado_en). ADMIN o GESTOR_STOCK."""
    return svc.reactivar_ingrediente(ingrediente_id)


@router.delete("/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[_admin_o_stock])
def eliminar_ingrediente(
    ingrediente_id: int, svc: IngredienteService = Depends(get_service)
):
    """Soft-delete: marca el ingrediente como eliminado. ADMIN o GESTOR_STOCK."""
    svc.eliminar_ingrediente(ingrediente_id)
