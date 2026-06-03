from fastapi import APIRouter, Depends, status, Query
from sqlmodel import Session
from typing import List, Optional

from core.database import get_session
from core.security import RoleChecker, TokenData, get_current_user_token
from .schemas import (
    AvanzarEstadoRequest,
    CancelarPedidoRequest,
    HistorialEstadoPublic,
    PedidoCreate,
    PedidoPublic,
    PedidoList,
)
from .service import PedidoService

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])

# ====================================================================
# DEPENDENCIAS REUTILIZABLES DE SEGURIDAD
# ====================================================================

def get_pedido_service(session: Session = Depends(get_session)) -> PedidoService:
    return PedidoService(session)


# ====================================================================
# ENDPOINTS PÚBLICOS/PROTEGIDOS
# ====================================================================

@router.post(
    "/",
    response_model=PedidoPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo pedido",
)
def crear_pedido(
    datos: PedidoCreate,
    current_user: TokenData = Depends(get_current_user_token),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Crea un nuevo pedido para el usuario autenticado.
    Valida productos, calcula totales y genera el historial inicial.
    """
    return svc.crear_pedido(int(current_user.id), datos)


@router.get(
    "/",
    response_model=PedidoList,
    summary="Listar pedidos con paginación",
)
def listar_pedidos(
    offset: int = Query(default=0, ge=0, description="Offset para paginación"),
    limit: int = Query(default=20, ge=1, le=100, description="Límite de resultados"),
    estado: Optional[str] = Query(default=None, description="Filtrar por código de estado (ej: PENDIENTE, CONFIRMADO)"),
    current_user: TokenData = Depends(get_current_user_token),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Lista pedidos con paginación.
    - CLIENTES ven solo sus propios pedidos.
    - ADMIN/GESTOR_PEDIDOS ven todos los pedidos del sistema.
    """
    return svc.listar_pedidos(
        usuario_id=int(current_user.id),
        roles=current_user.roles,
        offset=offset,
        limit=limit,
        estado=estado,
    )


@router.get(
    "/{pedido_id}",
    response_model=PedidoPublic,
    summary="Obtener detalle de un pedido",
)
def obtener_pedido(
    pedido_id: int,
    current_user: TokenData = Depends(get_current_user_token),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Obtiene los detalles de un pedido específico.
    CLIENTES solo pueden ver sus propios pedidos.
    ADMIN/GESTOR_PEDIDOS pueden ver cualquier pedido.
    """
    return svc.obtener_pedido(pedido_id, int(current_user.id), current_user.roles)


@router.get(
    "/{pedido_id}/historial",
    response_model=List[HistorialEstadoPublic],
    summary="Obtener historial de estados de un pedido",
)
def obtener_historial(
    pedido_id: int,
    current_user: TokenData = Depends(get_current_user_token),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Devuelve el historial completo de transiciones de estado de un pedido.
    Ordenado cronológicamente desde la creación hasta el estado actual.
    """
    return svc.obtener_historial(pedido_id, int(current_user.id), current_user.roles)


@router.patch(
    "/{pedido_id}/cancelar",
    response_model=PedidoPublic,
    summary="Cancelar un pedido",
)
def cancelar_pedido(
    pedido_id: int,
    datos: CancelarPedidoRequest,
    current_user: TokenData = Depends(get_current_user_token),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Cancela un pedido.
    - CLIENTES pueden cancelar solo desde PENDIENTE o CONFIRMADO.
    - ADMIN/GESTOR_PEDIDOS pueden cancelar desde cualquier estado excepto ENTREGADO/CANCELADO.
    """
    return svc.cancelar_pedido(
        pedido_id,
        datos.motivo,
        int(current_user.id),
        current_user.roles,
    )


# ====================================================================
# ENDPOINTS EXCLUSIVOS DE STAFF (ADMIN / GESTOR_PEDIDOS)
# ====================================================================

@router.patch(
    "/{pedido_id}/estado",
    response_model=PedidoPublic,
    summary="Avanzar estado de un pedido",
    dependencies=[Depends(RoleChecker(["ADMIN", "GESTOR_PEDIDOS"]))],
)
def avanzar_estado(
    pedido_id: int,
    datos: AvanzarEstadoRequest,
    current_user: TokenData = Depends(get_current_user_token),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Avanza el estado de un pedido siguiendo la máquina de estados finitos (FSM).
    Solo ADMIN y GESTOR_PEDIDOS pueden usar este endpoint.
    """
    return svc.avanzar_estado(pedido_id, datos, int(current_user.id))


@router.get(
    "/gestion/todos",
    response_model=PedidoList,
    tags=["Pedidos - Gestión"],
    summary="Listar todos los pedidos para administración",
    dependencies=[Depends(RoleChecker(["ADMIN", "GESTOR_PEDIDOS"]))],
)
def listar_todos_los_pedidos(
    offset: int = Query(default=0, ge=0, description="Offset para paginación"),
    limit: int = Query(default=20, ge=1, le=100, description="Límite de resultados"),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Lista TODOS los pedidos del sistema para panel de administración.
    Solo ADMIN y GESTOR_PEDIDOS.
    """
    return svc.obtener_todos_los_pedidos(offset, limit)