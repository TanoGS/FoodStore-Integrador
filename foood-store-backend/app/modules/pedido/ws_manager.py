"""
ConnectionManager in-process para WebSockets.

Mantiene un set de conexiones activas indexadas por:
- websocket (objeto FastAPI WebSocket)
- usuario_id (un usuario puede tener N conexiones, una por tab)
- sala (string arbitrario, p. ej. "staff:pedidos" o "user:42")

Es seguro para uso concurrente bajo asyncio (FastAPI corre todo en un
único event loop). Usamos un `asyncio.Lock` para serializar las
operaciones que tocan la estructura (connect, disconnect, join, leave).

Si en el futuro se quiere escalar a multi-instancia, este módulo es el
único punto a reemplazar: implementar la misma interfaz con Redis Pub/Sub.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gestor de conexiones WS en memoria."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        # websocket -> {usuario_id, salas}
        self._connections: Dict[WebSocket, _ConnectionInfo] = {}
        # sala -> set de websockets
        self._rooms: Dict[str, Set[WebSocket]] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(
        self,
        websocket: WebSocket,
        usuario_id: int,
        rooms: list[str],
    ) -> None:
        """
        Registra un websocket ya aceptado (`await websocket.accept()` lo
        hizo el router) en las salas indicadas.
        """
        async with self._lock:
            self._connections[websocket] = _ConnectionInfo(
                usuario_id=usuario_id, rooms=set(rooms)
            )
            for room in rooms:
                self._rooms.setdefault(room, set()).add(websocket)
            logger.info(
                "WS connect: usuario=%s salas=%s total_conns=%s",
                usuario_id, sorted(rooms), len(self._connections),
            )

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Saca un websocket del manager (idempotente). Llamar en el bloque
        `finally` del router para garantizar limpieza.
        """
        async with self._lock:
            info = self._connections.pop(websocket, None)
            if info is None:
                return
            for room in info.rooms:
                room_set = self._rooms.get(room)
                if room_set is not None:
                    room_set.discard(websocket)
                    if not room_set:
                        self._rooms.pop(room, None)
            logger.info(
                "WS disconnect: usuario=%s total_conns=%s",
                info.usuario_id, len(self._connections),
            )

    # ------------------------------------------------------------------
    # Salas
    # ------------------------------------------------------------------

    async def join_room(self, websocket: WebSocket, room: str) -> None:
        async with self._lock:
            info = self._connections.get(websocket)
            if info is None:
                return
            if room in info.rooms:
                return
            info.rooms.add(room)
            self._rooms.setdefault(room, set()).add(websocket)

    async def leave_room(self, websocket: WebSocket, room: str) -> None:
        async with self._lock:
            info = self._connections.get(websocket)
            if info is None:
                return
            if room not in info.rooms:
                return
            info.rooms.discard(room)
            room_set = self._rooms.get(room)
            if room_set is not None:
                room_set.discard(websocket)
                if not room_set:
                    self._rooms.pop(room, None)

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    async def broadcast(self, room: str, event: dict) -> int:
        """
        Envía `event` (dict ya serializado) a todos los websockets de la sala.
        Devuelve la cantidad de recipients a los que efectivamente llegó.

        Se hace una snapshot del set de websockets bajo el lock, y después
        se envía sin el lock (los `send_json` son awaitables y no pueden
        bloquear a otras operaciones del manager).
        """
        async with self._lock:
            recipients = list(self._rooms.get(room, ()))

        if not recipients:
            return 0

        sent = 0
        for ws in recipients:
            if ws.client_state != WebSocketState.CONNECTED:
                continue
            try:
                await ws.send_json(event)
                sent += 1
            except Exception as exc:  # noqa: BLE001
                # Si falla el envío, lo logueamos y dejamos que el router
                # lo limpie cuando detecte la desconexión.
                logger.warning("WS send falló (room=%s): %s", room, exc)

        return sent

    async def send_personal(self, websocket: WebSocket, event: dict) -> bool:
        """Envía un evento a una conexión puntual. Devuelve True si llegó."""
        if websocket.client_state != WebSocketState.CONNECTED:
            return False
        try:
            await websocket.send_json(event)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("WS send_personal falló: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Introspection (para logs / debug)
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        return {
            "conexiones": len(self._connections),
            "salas":      {room: len(s) for room, s in self._rooms.items()},
        }


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


class _ConnectionInfo:
    __slots__ = ("usuario_id", "rooms")

    def __init__(self, usuario_id: int, rooms: set[str]) -> None:
        self.usuario_id = usuario_id
        self.rooms      = rooms


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

# Una sola instancia por proceso. Se importa en routers y services.
ws_manager = ConnectionManager()
