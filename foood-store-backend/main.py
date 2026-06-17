"""
FoodStore Backend - Aplicación principal FastAPI.

Este módulo configura la aplicación FastAPI con:
- Lifespan (startup/shutdown)
- Middlewares: CORS, Rate Limiting
- Routers de la API (usuarios, pedidos, catálogo, etc.)
- WebSockets para pedidos en tiempo real
"""
import logging
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from core.config import settings
from core.rate_limit import RateLimitMiddleware
from core.exceptions import AppError, app_error_handler


# Configurar logging para que se muestren los mensajes de la aplicación
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


# =============================================================================
# MIDDLEWARE DE TIMING — loguea método, ruta, status y duración de cada request
# =============================================================================
class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        inicio = time.perf_counter()
        response = await call_next(request)
        duracion_ms = (time.perf_counter() - inicio) * 1000
        logger.info(
            "%s %s → %s  (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duracion_ms,
        )
        return response


from app.modules.usuario.router import router as usuarios_router
from app.modules.pedido.router import router as pedido_router
from app.modules.pedido.ws_router import router as pedido_ws_router
from app.modules.direccion.router import router as direccion_router
from app.modules.catalogo.router import router as catalogo_router
from app.modules.admin.router import router as admin_router, config_router as admin_config_router
from app.modules.pagos.router import router as pagos_router
from app.modules.imagenes.router import router as imagenes_router


# =============================================================================
# LIFESPAN — startup / shutdown
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "startup: %s v%s — entorno listo",
        settings.PROJECT_NAME,
        settings.VERSION,
    )
    yield
    logger.info("shutdown: cerrando %s", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Handler de excepciones de dominio (AppError y subclases)
app.add_exception_handler(AppError, app_error_handler)


# =============================================================================
# MIDDLEWARES
# Orden de registro (Starlette aplica en orden inverso al de add_middleware):
#   1. TimingMiddleware      — mide y loguea cada request completa
#   2. RateLimitMiddleware   — bloquea IPs con demasiados intentos fallidos
#   3. CORSMiddleware        — maneja preflight OPTIONS
# =============================================================================
app.add_middleware(TimingMiddleware)
app.add_middleware(RateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
)


@app.get("/")
def root():
    return {"message": "Bienvenido a la API de Food Store"}


# Rutas activas de la API
app.include_router(usuarios_router, prefix=settings.API_V1_STR)
app.include_router(pedido_router, prefix=settings.API_V1_STR)
app.include_router(pedido_ws_router, prefix=settings.API_V1_STR)
app.include_router(direccion_router, prefix=settings.API_V1_STR)
app.include_router(catalogo_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(admin_config_router, prefix=settings.API_V1_STR)
app.include_router(pagos_router, prefix=settings.API_V1_STR)
app.include_router(imagenes_router, prefix=settings.API_V1_STR)
