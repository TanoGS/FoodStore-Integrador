from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from core.database import get_session
from app.modules.ingrediente.schemas import (
    IngredienteCreate, IngredientePublic, IngredienteUpdate, IngredienteList,
)
from app.modules.ingrediente.service import IngredienteService

router = APIRouter(prefix="/ingredientes", tags=["Ingredientes"])


def get_ingrediente_service(session: Session = Depends(get_session)) -> IngredienteService:
    """Factory de dependencia: inyecta el servicio con su Session."""
    return IngredienteService(session)


# ── Endpoints ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=IngredientePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un ingrediente",
)
def crear_ingrediente(
    data: IngredienteCreate,
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredientePublic:
    return svc.crear(data)


@router.get(
    "/",
    response_model=IngredienteList,
    status_code=status.HTTP_200_OK,
    summary="Listar ingredientes activos (paginado)",
)
def listar_ingredientes(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredienteList:
    return svc.listar_activos(offset=offset, limit=limit)


@router.get(
    "/{id}",
    response_model=IngredientePublic,
    status_code=status.HTTP_200_OK,
    summary="Obtener ingrediente por ID",
)
def obtener_ingrediente(
    id: int,
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredientePublic:
    return svc.obtener_por_id(id)


@router.patch(
    "/{id}",
    response_model=IngredientePublic,
    status_code=status.HTTP_200_OK,
    summary="Actualización parcial de ingrediente",
)
def actualizar_ingrediente(
    id: int,
    data: IngredienteUpdate,
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredientePublic:
    return svc.actualizar(id, data)


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Soft delete de ingrediente",
)
def eliminar_ingrediente(
    id: int,
    svc: IngredienteService = Depends(get_ingrediente_service),
):
    return svc.eliminar_logicamente(id)


@router.post(
    "/{id}/restaurar",
    response_model=IngredientePublic,
    status_code=status.HTTP_200_OK,
    summary="Restaurar ingrediente eliminado (revertir soft-delete)",
)
def restaurar_ingrediente(
    id: int,
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredientePublic:
    return svc.restaurar(id)