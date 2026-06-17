"""
core/rate_limit.py
==================
Middleware de rate limiting para endpoints de autenticación.

Especificación (TPI v6.0 — sección 4.3):
  - Máximo 5 intentos fallidos por IP en una ventana de 15 minutos.
  - Aplica a login (/api/v1/usuarios/login) y registro (/api/v1/usuarios/registro).
  - Responde HTTP 429 con header Retry-After al superar el límite.

Implementación:
  - Algoritmo Fixed Window (simple, sin dependencias externas).
  - Estado en memoria — válido para una sola instancia. En producción
    multi-worker se reemplazaría por Redis.
  - Solo cuenta respuestas 4xx/5xx del endpoint como "intentos fallidos".
    Logins exitosos (2xx) NO consumen el contador.
"""
import time
import threading
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


# Rutas protegidas por el rate limiter (sufijos sin prefix, se compara con endswith)
_AUTH_PATHS = (
    "/usuarios/login",
    "/usuarios/registro",
)

# Configuración de la ventana
_MAX_INTENTOS = 5       # intentos fallidos máximos
_VENTANA_SEG  = 15 * 60 # 15 minutos en segundos


class _Contador:
    """Estado de intentos para una IP dentro de la ventana activa."""
    __slots__ = ("intentos", "ventana_inicio")

    def __init__(self) -> None:
        self.intentos: int = 0
        self.ventana_inicio: float = time.monotonic()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware que limita intentos fallidos de autenticación por IP.

    El conteo se resetea automáticamente al vencer la ventana de 15 min.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self._contadores: dict[str, _Contador] = defaultdict(_Contador)
        self._lock = threading.Lock()

    def _es_ruta_auth(self, path: str) -> bool:
        return any(path.endswith(ruta) for ruta in _AUTH_PATHS)

    def _obtener_ip(self, request: Request) -> str:
        # Respeta X-Forwarded-For para entornos con proxy/ngrok.
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        if not self._es_ruta_auth(request.url.path):
            return await call_next(request)

        ip = self._obtener_ip(request)

        # Verificar límite ANTES de procesar la request
        with self._lock:
            contador = self._contadores[ip]
            ahora = time.monotonic()

            # Resetear ventana si expiró
            if ahora - contador.ventana_inicio >= _VENTANA_SEG:
                contador.intentos = 0
                contador.ventana_inicio = ahora

            if contador.intentos >= _MAX_INTENTOS:
                tiempo_restante = int(
                    _VENTANA_SEG - (ahora - contador.ventana_inicio)
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Demasiados intentos. Intentá de nuevo más tarde.",
                        "code":   "RATE_LIMIT_EXCEEDED",
                    },
                    headers={"Retry-After": str(tiempo_restante)},
                )

        # Procesar la request normalmente
        response = await call_next(request)

        # Contar solo respuestas fallidas (4xx / 5xx)
        if response.status_code >= 400:
            with self._lock:
                contador = self._contadores[ip]
                ahora = time.monotonic()
                # Re-chequear ventana por si expiró durante el procesamiento
                if ahora - contador.ventana_inicio >= _VENTANA_SEG:
                    contador.intentos = 0
                    contador.ventana_inicio = ahora
                contador.intentos += 1

        return response
