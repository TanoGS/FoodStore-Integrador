from fastapi import APIRouter, Depends, status
from typing import List
from sqlmodel import Session

from core.database import get_session
from core.security import get_current_user_token, TokenData
from .schemas import DireccionCreate, DireccionUpdate, DireccionPublic
from .service import DireccionService

router = APIRouter(prefix="/direcciones", tags=["Direcciones"])


def get_svc(session: Session = Depends(get_session)) -> DireccionService:
    return DireccionService(session)


@router.post("", response_model=DireccionPublic, status_code=status.HTTP_201_CREATED)
def crear_direccion(
    datos: DireccionCreate,
    token: TokenData = Depends(get_current_user_token),
    svc: DireccionService = Depends(get_svc),
):
    """Agrega una dirección de entrega al usuario autenticado."""
    return svc.agregar_direccion(int(token.id), datos)


@router.get("", response_model=List[DireccionPublic])
def listar_direcciones(
    token: TokenData = Depends(get_current_user_token),
    svc: DireccionService = Depends(get_svc),
):
    """Lista las direcciones activas del usuario autenticado."""
    return svc.listar_mis_direcciones(int(token.id))


@router.get("/{direccion_id}", response_model=DireccionPublic)
def obtener_direccion(
    direccion_id: int,
    token: TokenData = Depends(get_current_user_token),
    svc: DireccionService = Depends(get_svc),
):
    """Obtiene una dirección por ID (solo propias)."""
    return svc.obtener_direccion(direccion_id, int(token.id))


@router.patch("/{direccion_id}", response_model=DireccionPublic)
def actualizar_direccion(
    direccion_id: int,
    datos: DireccionUpdate,
    token: TokenData = Depends(get_current_user_token),
    svc: DireccionService = Depends(get_svc),
):
    """Actualiza campos de una dirección (solo propias)."""
    return svc.actualizar_direccion(direccion_id, int(token.id), datos)


@router.patch("/{direccion_id}/principal", response_model=DireccionPublic)
def marcar_principal(
    direccion_id: int,
    token: TokenData = Depends(get_current_user_token),
    svc: DireccionService = Depends(get_svc),
):
    """Marca esta dirección como predeterminada y desmarca las demás."""
    return svc.marcar_principal(direccion_id, int(token.id))


@router.delete("/{direccion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_direccion(
    direccion_id: int,
    token: TokenData = Depends(get_current_user_token),
    svc: DireccionService = Depends(get_svc),
):
    """Soft-delete. Falla con 409 si la dirección es la principal."""
    svc.eliminar_direccion(direccion_id, int(token.id))


@router.patch("/{direccion_id}/reactivar", response_model=DireccionPublic)
def reactivar_direccion(
    direccion_id: int,
    token: TokenData = Depends(get_current_user_token),
    svc: DireccionService = Depends(get_svc),
):
    """Reactiva una dirección previamente eliminada (solo propias)."""
    return svc.reactivar_direccion(direccion_id, int(token.id))