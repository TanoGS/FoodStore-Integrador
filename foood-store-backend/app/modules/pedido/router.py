from fastapi import APIRouter, Depends, status, Query
from sqlmodel import Session
from typing import List, Optional

from core.database import get_session
from core.security import RoleChecker, TokenData, get_current_user_token
from .events import (
    ROOM_STAFF_PEDIDOS,
    room_user,
    serialize_pedido_creado,
    serialize_pedido_estado_cambiado,
    serialize_pedido_mio_actualizado,
    serialize_stock_alerta,
)
from .schemas import (
    AvanzarEstadoRequest,
    CancelarPedidoRequest,
    HistorialEstadoPublic,
    PedidoCreate,
    PedidoPublic,
    PedidoList,
    PedidoAdmin,
    PedidoAdminList,
)
from .service import PedidoService
from .ws_manager import ws_manager

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
async def crear_pedido(
    datos: PedidoCreate,
    current_user: TokenData = Depends(get_current_user_token),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Crea un nuevo pedido para el usuario autenticado.
    Valida productos, calcula totales y genera el historial inicial.

    Al confirmarse, emite por WebSocket:
    - `pedido.creado`           → sala `staff:pedidos`
    - `pedido.mio.actualizado`  → sala `user:{usuario_id}` del cliente
    """
    resultado = svc.crear_pedido(int(current_user.id), datos)

    # Broadcast a la sala de staff
    await ws_manager.broadcast(
        ROOM_STAFF_PEDIDOS,
        serialize_pedido_creado(resultado.pedido),
    )
    # Broadcast al cliente dueño del pedido
    await ws_manager.broadcast(
        room_user(resultado.pedido.usuario_id),
        serialize_pedido_mio_actualizado(
            id_=resultado.pedido.id,
            estado_codigo=resultado.pedido.estado_codigo,
            actualizado_en=(
                resultado.pedido.actualizado_en.isoformat()
                if resultado.pedido.actualizado_en
                else resultado.pedido.creado_en.isoformat()
            ),
        ),
    )

    return resultado.pedido


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
    - ADMIN / GESTOR_PEDIDOS / CAJERO / COCINA ven todos los pedidos del sistema.
    """
    return svc.listar_pedidos(
        usuario_id=int(current_user.id),
        roles=current_user.roles,
        offset=offset,
        limit=limit,
        estado=estado,
    )


# ====================================================================
# ENDPOINTS EXCLUSIVOS DE STAFF (ADMIN / GESTOR_PEDIDOS / CAJERO / COCINA)
# ====================================================================
# NOTA: estas rutas con path fijo (ej. /admin, /gestion/todos) deben
# definirse ANTES de las rutas con path params dinámicos (ej. /{pedido_id})
# para que FastAPI las matchee correctamente (orden de definición).
# ====================================================================

@router.get(
    "/admin",
    response_model=PedidoAdminList,
    tags=["Pedidos - Gestión"],
    summary="Listar pedidos enriquecidos para GestorPedidos (staff)",
    dependencies=[Depends(RoleChecker(["ADMIN", "GESTOR_PEDIDOS", "CAJERO", "COCINA"]))],
)
def listar_pedidos_admin(
    offset:   int = Query(default=0,  ge=0, description="Offset para paginación"),
    limit:    int = Query(default=50, ge=1, le=200, description="Límite de resultados"),
    periodo:  Optional[str] = Query(
        default=None,
        description="Filtrar por período: 'DIARIO' (hoy), 'MENSUAL' (mes actual) o None (todos)",
    ),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Endpoint optimizado para el GestorPedidos staff.
    Devuelve pedidos enriquecidos con:
    - Nombre y email del cliente
    - Dirección completa (calle, número, ciudad, referencia)
    - Forma de pago en formato legible
    - Detalle de productos (snapshot al momento de la compra)

    Filtro de período:
    - 'DIARIO': solo pedidos de hoy (00:00 a 23:59)
    - 'MENSUAL': pedidos del mes actual (1° al último día)
    - None o cualquier otro valor: todos los pedidos

    Roles permitidos: ADMIN, GESTOR_PEDIDOS, CAJERO y COCINA.
    """
    return svc.obtener_todos_admin(periodo=periodo, offset=offset, limit=limit)


@router.get(
    "/gestion/todos",
    response_model=PedidoList,
    tags=["Pedidos - Gestión"],
    summary="Listar todos los pedidos para administración",
    dependencies=[Depends(RoleChecker(["ADMIN", "GESTOR_PEDIDOS", "CAJERO", "COCINA"]))],
)
def listar_todos_los_pedidos(
    offset: int = Query(default=0, ge=0, description="Offset para paginación"),
    limit: int = Query(default=20, ge=1, le=100, description="Límite de resultados"),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Lista TODOS los pedidos del sistema para panel de operación.
    Roles permitidos: ADMIN, GESTOR_PEDIDOS, CAJERO y COCINA.
    """
    return svc.obtener_todos_los_pedidos(offset, limit)


# ====================================================================
# ENDPOINTS CON PATH PARAMS DINÁMICOS
# (definidos al final para que las rutas fijas tengan prioridad)
# ====================================================================

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
    Roles de staff (ADMIN / GESTOR_PEDIDOS / CAJERO / COCINA) pueden ver cualquier pedido.
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
async def cancelar_pedido(
    pedido_id: int,
    datos: CancelarPedidoRequest,
    current_user: TokenData = Depends(get_current_user_token),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Cancela un pedido.
    - CLIENTES pueden cancelar solo desde PENDIENTE o CONFIRMADO.
    - Roles de staff pueden cancelar desde cualquier estado excepto ENTREGADO/CANCELADO.

    Al confirmarse, emite por WebSocket:
    - `pedido.estado.cambiado`   → sala `staff:pedidos`
    - `pedido.mio.actualizado`   → sala `user:{usuario_id}` del cliente
    """
    actor_id = int(current_user.id)
    resultado = svc.cancelar_pedido(
        pedido_id, datos.motivo, actor_id, current_user.roles,
    )

    # Broadcast a la sala de staff (payload completo con historial)
    await ws_manager.broadcast(
        ROOM_STAFF_PEDIDOS,
        serialize_pedido_estado_cambiado(
            pedido=resultado.pedido,
            estado_desde=resultado.historial.estado_desde,
            estado_hacia=resultado.historial.estado_hacia,
            usuario_actor_id=resultado.historial.usuario_id,
            motivo=resultado.historial.motivo,
            historial=resultado.historial,
        ),
    )
    # Broadcast al cliente dueño del pedido (payload mínimo)
    await ws_manager.broadcast(
        room_user(resultado.pedido.usuario_id),
        serialize_pedido_mio_actualizado(
            id_=resultado.pedido.id,
            estado_codigo=resultado.pedido.estado_codigo,
            actualizado_en=(
                resultado.pedido.actualizado_en.isoformat()
                if resultado.pedido.actualizado_en
                else None
            ),
        ),
    )

    return resultado.pedido


@router.patch(
    "/{pedido_id}/estado",
    response_model=PedidoPublic,
    summary="Avanzar estado de un pedido",
    dependencies=[Depends(RoleChecker(["ADMIN", "GESTOR_PEDIDOS", "CAJERO", "COCINA"]))],
)
async def avanzar_estado(
    pedido_id: int,
    datos: AvanzarEstadoRequest,
    current_user: TokenData = Depends(get_current_user_token),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Avanza el estado de un pedido siguiendo la máquina de estados finitos (FSM).
    Roles permitidos: ADMIN, GESTOR_PEDIDOS, CAJERO y COCINA.
    La lógica de qué transiciones puede hacer cada rol se valida en el servicio.

    Al confirmarse, emite por WebSocket:
    - `pedido.estado.cambiado`   → sala `staff:pedidos`
    - `pedido.mio.actualizado`   → sala `user:{usuario_id}` del cliente
    - `stock.alerta`             → sala `staff:pedidos` (si algún ingrediente quedó bajo stock de seguridad)
    """
    actor_id = int(current_user.id)
    resultado = svc.avanzar_estado(pedido_id, datos, actor_id)

    # Broadcast a la sala de staff (payload completo con historial)
    await ws_manager.broadcast(
        ROOM_STAFF_PEDIDOS,
        serialize_pedido_estado_cambiado(
            pedido=resultado.pedido,
            estado_desde=resultado.historial.estado_desde,
            estado_hacia=resultado.historial.estado_hacia,
            usuario_actor_id=resultado.historial.usuario_id,
            motivo=resultado.historial.motivo,
            historial=resultado.historial,
        ),
    )
    # Broadcast al cliente dueño del pedido (payload mínimo)
    await ws_manager.broadcast(
        room_user(resultado.pedido.usuario_id),
        serialize_pedido_mio_actualizado(
            id_=resultado.pedido.id,
            estado_codigo=resultado.pedido.estado_codigo,
            actualizado_en=(
                resultado.pedido.actualizado_en.isoformat()
                if resultado.pedido.actualizado_en
                else None
            ),
        ),
    )

    # ── Alerta de stock bajo (stock ya persisted tras commit del UoW) ──
    if resultado.stock_bajo:
        await ws_manager.broadcast(
            ROOM_STAFF_PEDIDOS,
            serialize_stock_alerta(resultado.stock_bajo),
        )

    return resultado.pedido
