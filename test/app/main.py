"""
Módulo: app/main.py
===================

Punto de entrada de la aplicación FastAPI.

Acá se conectan TODAS las piezas:
  - Lifespan (startup/shutdown).
  - Middlewares (Logging, Timing, RateLimit).
  - Exception handlers (formato JSON unificado).
  - Routers de cada módulo.
  - CORS.

Es el ÚNICO archivo donde se "ensambla" todo. Mantenerlo limpio facilita
entender la app de un vistazo.
"""

# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
# `FastAPI` es la app principal. `Request` para type hints.
# `lifespan` es el context manager async que reemplaza al viejo
# `@app.on_event("startup")` (deprecado en FastAPI 0.93+).
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request

# `CORSMiddleware` para habilitar CORS (Cross-Origin Resource Sharing).
# Sin esto, un frontend en http://localhost:3000 no puede pegarle a una
# API en http://localhost:8000.
from fastapi.middleware.cors import CORSMiddleware

# Logger y config.
from app.core.config import settings
from app.core.logger import get_logger, setup_logging

# Middlewares.
from app.core.middleware.logging_middleware import LoggingMiddleware
from app.core.middleware.timing_middleware import TimingMiddleware
from app.core.rate_limit.rate_limit_middleware import RateLimitMiddleware

# Exception handlers.
from app.core.exceptions.exception_handlers import register_exception_handlers

# Routers de cada módulo.
from app.modules.productos.router import router as productos_router
from app.modules.usuarios.router import router as usuarios_router

# Seed (lo ejecutamos en el startup del lifespan).
from app.db.seed import seed_database


# ---------------------------------------------------------------------------
# LOGGER (a nivel módulo)
# ---------------------------------------------------------------------------
# Configuramos el logger UNA vez al importar el módulo.
setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# LIFESPAN: startup + shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager de vida de la app.

    - Startup: código que se ejecuta ANTES de que la app acepte requests.
      Acá creamos las tablas, corremos el seed y logueamos el evento.
    - Shutdown: código que se ejecuta cuando la app se cierra (Ctrl+C,
      deploy nuevo, etc.). Cerramos conexiones, logueamos, etc.

    ¿Por qué `asynccontextmanager` y no `@app.on_event`?
    ----------------------------------------------------
    `@app.on_event` está deprecado. El patrón moderno es un async context
    manager con `yield`. Lo que va ANTES del yield es startup; lo que va
    DESPUÉS es shutdown.
    """
    # ============== STARTUP ==============
    logger.info(
        "app.startup",
        extra={
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        },
    )

    # Corremos el seed (crea admin inicial y productos de ejemplo).
    # Envolvemos en try/except para que un fallo de seed no impida que
    # la app arranque (puede haber migraciones manuales pendientes).
    try:
        seed_database()
        logger.info("seed.completed")
    except Exception as e:
        logger.warning(f"seed.failed (continuamos sin seed): {e}")

    yield  # ← La app queda escuchando requests acá.

    # ============== SHUTDOWN ==============
    logger.info("app.shutdown")


# ---------------------------------------------------------------------------
# CREACIÓN DE LA APP
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "API de ejemplo para FastAPI + SQLModel + JWT, con middlewares, "
        "exception handlers globales, rate limiting y suite de tests con "
        "pytest + TestClient."
    ),
    # OpenAPI tags metadata: aparecen en /docs como secciones agrupadas.
    openapi_tags=[
        {"name": "usuarios", "description": "Registro, login, gestión de usuarios."},
        {"name": "productos", "description": "CRUD de productos con búsqueda paginada."},
    ],
    # Pasamos el lifespan para que se ejecute en startup/shutdown.
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# MIDDLEWARES
# ---------------------------------------------------------------------------
# ⚠️ El ORDEN de los middlewares importa: se ejecutan en orden de
# declaración para la request, y en orden INVERSO para la response.

# 1) Rate limit: lo ponemos PRIMERO para cortar requests abusivas antes
#    de gastar trabajo en logging/auth/etc.
app.add_middleware(RateLimitMiddleware)

# 2) Logging: registramos cada request con su duración total. Va DESPUÉS
#    del rate limit (si rate limit cortó, el log lo refleja como 429).
app.add_middleware(LoggingMiddleware)

# 3) Timing: mide el tiempo de procesamiento interno. Es un middleware
#    "transparente" que solo agrega headers, no loguea.
app.add_middleware(TimingMiddleware)

# 4) CORS: maneja los headers de Cross-Origin. DEBE ir último para que
#    su respuesta (Access-Control-Allow-Origin) se agregue a TODAS las
#    responses, incluso las 4xx/5xx de los middlewares anteriores.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,           # lista de orígenes permitidos
    allow_credentials=True,                       #允许 enviar cookies
    allow_methods=["*"],                           # todos los métodos HTTP
    allow_headers=["*"],                           # todos los headers
)


# ---------------------------------------------------------------------------
# EXCEPTION HANDLERS (formato JSON unificado)
# ---------------------------------------------------------------------------
# Registra los 5 handlers definidos en `app/core/exceptions/exception_handlers.py`:
#   - app_error_handler (errores de dominio)
#   - http_exception_handler (HTTPException de FastAPI)
#   - validation_exception_handler (RequestValidationError de Pydantic)
#   - sqlalchemy_exception_handler (IntegrityError, etc.)
#   - unhandled_exception_handler (catch-all)
register_exception_handlers(app)


# ---------------------------------------------------------------------------
# ROUTERS
# ---------------------------------------------------------------------------
# Cada router tiene su `prefix` para namespace.
# `tags` ya están definidas en el router mismo.
app.include_router(
    usuarios_router,
    prefix="/usuarios",
    tags=["usuarios"],
)

app.include_router(
    productos_router,
    prefix="/productos",
    tags=["productos"],
)


# ---------------------------------------------------------------------------
# ENDPOINT RAÍZ: health check simple
# ---------------------------------------------------------------------------
@app.get(
    "/",
    summary="Health check",
    description="Devuelve info básica de la API. Útil para smoke tests.",
    tags=["health"],
)
def root() -> dict:
    """
    Health check minimalista. En producción harías algo más completo:
      - Ping a la DB.
      - Chequeo de memoria.
      - Versión del deploy.
    """
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "ok",
        "environment": settings.ENVIRONMENT,
    }

