from typing import List

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from core.database import get_session
from core.security import RoleChecker, TokenData, get_current_user_token
from .schemas import (
    AvanzarEstadoRequest,
    CancelarPedidoRequest,
    HistorialEstadoPublic,
    PedidoCreate,
    PedidoPublic,
)
from .service import PedidoService

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])

# Dependencia reutilizable para proteger endpoints de staff
_solo_staff = Depends(RoleChecker(["ADMIN", "GESTOR_PEDIDOS"]))


def _svc(session: Session = Depends(get_session)) -> PedidoService:
    return PedidoService(session)


@router.post(
    "/",
    response_model=PedidoPublic,
    status_code=status.HTTP_201_CREATED,
)
def crear_pedido(
    datos: PedidoCreate,
    current_user: TokenData = Depends(get_current_user_token),
    svc: PedidoService = Depends(_svc),
):
    return svc.crear_pedido(int(current_user.id), datos)


@router.get("/", response_model=List[PedidoPublic])
def listar_pedidos(
    current_user: TokenData = Depends(get_current_user_token),
    svc: PedidoService = Depends(_svc),
):
    return svc.listar_pedidos(int(current_user.id), current_user.roles)


@router.get("/{pedido_id}", response_model=PedidoPublic)
def obtener_pedido(
    pedido_id: int,
    current_user: TokenData = Depends(get_current_user_token),
    svc: PedidoService = Depends(_svc),
):
    return svc.obtener_pedido(pedido_id, int(current_user.id), current_user.roles)


@router.get("/{pedido_id}/historial", response_model=List[HistorialEstadoPublic])
def obtener_historial(
    pedido_id: int,
    current_user: TokenData = Depends(get_current_user_token),
    svc: PedidoService = Depends(_svc),
):
    return svc.obtener_historial(pedido_id, int(current_user.id), current_user.roles)


@router.patch(
    "/{pedido_id}/estado",
    response_model=PedidoPublic,
    dependencies=[_solo_staff],
)
def avanzar_estado(
    pedido_id: int,
    datos: AvanzarEstadoRequest,
    current_user: TokenData = Depends(get_current_user_token),
    svc: PedidoService = Depends(_svc),
):
    return svc.avanzar_estado(pedido_id, datos, int(current_user.id))


@router.patch("/{pedido_id}/cancelar", response_model=PedidoPublic)
def cancelar_pedido(
    pedido_id: int,
    datos: CancelarPedidoRequest,
    current_user: TokenData = Depends(get_current_user_token),
    svc: PedidoService = Depends(_svc),
):
    return svc.cancelar_pedido(
        pedido_id, datos.motivo, int(current_user.id), current_user.roles
    )
