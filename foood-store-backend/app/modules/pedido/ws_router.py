"""
Router de WebSockets para el módulo de pedidos.

Endpoint único: WS /ws/pedidos?token=<JWT>

Cualquier usuario autenticado puede conectar. Al hacerlo se une a:
- `user:{id}` → su sala privada (siempre).
- `staff:pedidos` → solo si tiene al menos un rol de staff operativo
  sobre pedidos (alineado con `_ROLES_STAFF_PEDIDOS` del service).

El cliente puede mandar mensajes JSON. Soportados:
- `{"type": "ping"}` → respondemos `{"type": "pong", "t": <now>}`
- `{"type": "subscribe", "pedido_id": <int>}` → (reservado para futuro
   seguimiento fino de un pedido; hoy no es necesario porque la sala
   `staff:pedidos` ya emite todos los cambios)

El servidor, ante una desconexión, limpia al websocket del manager.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from core.security import decode_access_token

from .events import ROOM_STAFF_PEDIDOS, room_user
from .ws_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Pedidos - WebSocket"])

# Roles con acceso a la sala global de gestión (alineado con service.py)
_STAFF_ROLES = {"ADMIN", "GESTOR_PEDIDOS", "CAJERO", "COCINA"}


@router.websocket("/ws/pedidos")
async def websocket_pedidos(
    websocket: WebSocket,
    token: str = Query(..., description="JWT de acceso (mismo que Authorization Bearer)"),
) -> None:
    """
    Conexión WebSocket autenticada por JWT en query string.
    """
    # 1) Validar token. Si falla, cerramos SIN aceptar la conexión.
    #
    # Metodología "WebSockets con JWT en FastAPI" (Unidad 5):
    #   "JWT antes del handshake — valida el token y el rol antes de
    #    llamar a ws.accept(). Una conexión no autenticada NUNCA debe
    #    llegar al ConnectionManager."
    #
    # No llamamos a websocket.accept(): al salir del handler sin
    # aceptar, FastAPI/Starlette cierra la conexión con 403, que es
    # exactamente lo que queremos para un handshake no autenticado.
    try:
        user = decode_access_token(token)
        usuario_id = int(user.id)
        logger.info(f"WS: token válido para usuario_id={usuario_id}, roles={user.roles}")
    except (JWTError, ValueError, Exception) as exc:  # noqa: BLE001
        logger.warning(f"WS rechazado: token inválido o expirado (cierre sin accept) - Error: {type(exc).__name__}: {exc}")
        return

    # 2) Determinar salas según el rol del usuario
    rooms: list[str] = [room_user(usuario_id)]
    if any(r in _STAFF_ROLES for r in user.roles):
        rooms.append(ROOM_STAFF_PEDIDOS)

    # 3) Aceptar y registrar
    await websocket.accept()
    await ws_manager.connect(websocket, usuario_id=usuario_id, rooms=rooms)

    # Mensaje de bienvenida (útil para que el cliente sepa que se conectó)
    await ws_manager.send_personal(
        websocket,
        {
            "type":    "hello",
            "payload": {
                "usuario_id": usuario_id,
                "rooms":      rooms,
                "server_ts":  int(time.time() * 1000),
            },
        },
    )

    # 4) Loop de lectura. Procesamos ping/pong y logueamos el resto.
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg: Any = json.loads(raw)
            except json.JSONDecodeError:
                # Si no es JSON válido, respondemos con un error y seguimos
                await ws_manager.send_personal(
                    websocket,
                    {"type": "error", "payload": {"detail": "JSON inválido"}},
                )
                continue

            mtype = msg.get("type") if isinstance(msg, dict) else None

            if mtype == "ping":
                await ws_manager.send_personal(
                    websocket,
                    {"type": "pong", "payload": {"t": int(time.time() * 1000)}},
                )
            elif mtype == "subscribe":
                # Hook para futuro: p. ej. suscribirse a un pedido puntual.
                # Hoy no se usa porque la sala `staff:pedidos` ya emite todo.
                pedido_id = msg.get("pedido_id")
                logger.debug("WS subscribe pedido_id=%s (no-op)", pedido_id)
            else:
                # Mensaje desconocido: lo logueamos a nivel debug y seguimos.
                logger.debug("WS mensaje no reconocido: %s", msg)

    except WebSocketDisconnect:
        # Cliente cerró (cierre de tab, refresh, navegación).
        logger.info("WS desconectado por cliente: usuario=%s", usuario_id)
    except Exception as exc:  # noqa: BLE001
        # Cualquier otro error lo logueamos.
        logger.exception("WS error inesperado: usuario=%s exc=%s", usuario_id, exc)
    finally:
        # 5) Limpieza garantizada
        await ws_manager.disconnect(websocket)
