"""
Tipos de eventos que emite el broadcaster de WebSocket.

El contrato con el frontend (ver food-store-frontend/src/services/websocket.service.ts)
es que cada evento es un JSON con la forma:

    {
        "type": "<event_type>",
        "payload": { ... },       # depende del evento
        "ts": <unix_millis>        # timestamp del servidor
    }

Los payloads se modelan con Pydantic para tener un único punto de verdad.
"""

from typing import List, Optional

from pydantic import BaseModel

from .schemas import HistorialEstadoPublic, PedidoPublic


# ---------------------------------------------------------------------------
# Salas
# ---------------------------------------------------------------------------

ROOM_STAFF_PEDIDOS = "staff:pedidos"


def room_user(usuario_id: int) -> str:
    """Sala privada de un usuario concreto (su id)."""
    return f"user:{usuario_id}"


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------


class PedidoCreadoPayload(BaseModel):
    """Payload de `pedido.creado`. Se envía a la sala de staff."""

    pedido: PedidoPublic


class PedidoEstadoCambiadoPayload(BaseModel):
    """
    Payload de `pedido.estado.cambiado`.
    Se envía a la sala de staff (con el pedido completo y el historial) y
    también a la sala del dueño del pedido (con un subset mínimo).
    """

    pedido:                PedidoPublic
    estado_desde:          Optional[str] = None
    estado_hacia:          str
    usuario_actor_id:      Optional[int] = None
    motivo:                Optional[str] = None
    historial:             Optional[HistorialEstadoPublic] = None


class PedidoMioActualizadoPayload(BaseModel):
    """
    Payload liviano que se envía a la sala `user:{id}`.
    Solo lo esencial para que el cliente refresque su tarjeta de pedido
    sin recibir toda la información administrativa.
    """

    id:               int
    estado_codigo:    str
    actualizado_en:   Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers de serialización a dict (lo que va por el WS)
# ---------------------------------------------------------------------------


def serialize_pedido_creado(pedido: PedidoPublic) -> dict:
    return {
        "type":    "pedido.creado",
        "payload": PedidoCreadoPayload(pedido=pedido).model_dump(mode="json"),
    }


def serialize_pedido_estado_cambiado(
    pedido: PedidoPublic,
    estado_desde: Optional[str],
    estado_hacia: str,
    usuario_actor_id: Optional[int],
    motivo: Optional[str],
    historial: Optional[HistorialEstadoPublic],
) -> dict:
    return {
        "type": "pedido.estado.cambiado",
        "payload": PedidoEstadoCambiadoPayload(
            pedido=pedido,
            estado_desde=estado_desde,
            estado_hacia=estado_hacia,
            usuario_actor_id=usuario_actor_id,
            motivo=motivo,
            historial=historial,
        ).model_dump(mode="json"),
    }


def serialize_pedido_mio_actualizado(
    id_: int,
    estado_codigo: str,
    actualizado_en: Optional[str],
) -> dict:
    return {
        "type": "pedido.mio.actualizado",
        "payload": PedidoMioActualizadoPayload(
            id=id_,
            estado_codigo=estado_codigo,
            actualizado_en=actualizado_en,
        ).model_dump(mode="json"),
    }


# ---------------------------------------------------------------------------
# Payloads — Stock
# ---------------------------------------------------------------------------


class IngredienteCritico(BaseModel):
    """Un ingrediente que quedó por debajo de su stock de seguridad."""

    id: int
    nombre: str
    stock_actual: float
    stock_seguridad: float
    unidad: str


class StockAlertaPayload(BaseModel):
    """Payload de `stock.alerta`. Se envía a la sala de staff."""

    ingredientes_criticos: List[IngredienteCritico]
    # Cantidad de items en la alerta para que el badge sea útil
    total: int


def serialize_stock_alerta(ingredientes: List[dict]) -> dict:
    """
    Serializa el evento de alerta de stock bajo para broadcast por WebSocket.

    Args:
        ingredientes: Lista de dicts con campos:
            - id, nombre, stock_actual, stock_seguridad, unidad
    """
    criticos = [
        IngredienteCritico(
            id=i["id"],
            nombre=i["nombre"],
            stock_actual=i["stock_actual"],
            stock_seguridad=i["stock_seguridad"],
            unidad=i["unidad"],
        )
        for i in ingredientes
    ]
    return {
        "type": "stock.alerta",
        "payload": StockAlertaPayload(
            ingredientes_criticos=criticos,
            total=len(criticos),
        ).model_dump(mode="json"),
    }
