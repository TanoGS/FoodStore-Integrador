from fastapi import APIRouter, Depends, status
from sqlmodel import Session
from typing import List

from core.database import get_session
from .schemas import (
    IngredienteCreate,
    IngredienteUpdate,
    IngredientePublic,
)
from .service import IngredienteService

router = APIRouter(tags=["Inventario - Depósito"])


def get_service(session: Session = Depends(get_session)) -> IngredienteService:
    return IngredienteService(session)


# ==============================================================================
# Ingredientes
# ==============================================================================
@router.post(
    "/ingredientes",
    response_model=IngredientePublic,
    status_code=status.HTTP_201_CREATED,
)
def crear_ingrediente(
    data: IngredienteCreate, svc: IngredienteService = Depends(get_service)
):
    """Da de alta un insumo con su costo y unidad de medida."""
    return svc.crear_ingrediente(data)


@router.get("/ingredientes", response_model=List[IngredientePublic])
def listar_ingredientes(
    offset: int = 0,
    limit: int = 200,
    incluir_eliminados: bool = False,
    svc: IngredienteService = Depends(get_service),
):
    """Lista la materia prima. Con incluir_eliminados=true devuelve también los dados de baja."""
    return svc.listar_ingredientes(offset, limit, incluir_eliminados)


@router.get("/ingredientes/{ingrediente_id}", response_model=IngredientePublic)
def obtener_ingrediente(
    ingrediente_id: int, svc: IngredienteService = Depends(get_service)
):
    return svc.obtener_ingrediente(ingrediente_id)


@router.patch("/ingredientes/{ingrediente_id}", response_model=IngredientePublic)
def actualizar_ingrediente(
    ingrediente_id: int,
    data: IngredienteUpdate,
    svc: IngredienteService = Depends(get_service),
):
    return svc.actualizar_ingrediente(ingrediente_id, data)


@router.patch("/ingredientes/{ingrediente_id}/reactivar", response_model=IngredientePublic)
def reactivar_ingrediente(
    ingrediente_id: int, svc: IngredienteService = Depends(get_service)
):
    """Restaura un ingrediente dado de baja (limpia eliminado_en)."""
    return svc.reactivar_ingrediente(ingrediente_id)


@router.delete(
    "/ingredientes/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT
)
def eliminar_ingrediente(
    ingrediente_id: int, svc: IngredienteService = Depends(get_service)
):
    """Soft-delete: marca el ingrediente como eliminado."""
    svc.eliminar_ingrediente(ingrediente_id)
