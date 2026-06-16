"""
FoodStore Backend - Aplicación principal FastAPI.

Este módulo configura la aplicación FastAPI con:
- Routers de la API (usuarios, pedidos, catálogo, etc.)
- WebSockets para pedidos en tiempo real
- CORS configurado para desarrollo local
"""
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware
from core.config import settings


# Configurar logging para que se muestren los mensajes de la aplicación
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)


from app.modules.usuario.router import router as usuarios_router
from app.modules.pedido.router import router as pedido_router
from app.modules.pedido.ws_router import router as pedido_ws_router
from app.modules.direccion.router import router as direccion_router
from app.modules.catalogo.router import router as catalogo_router
from app.modules.admin.router import router as admin_router, config_router as admin_config_router
from app.modules.pagos.router import router as pagos_router
from app.modules.imagenes.router import router as imagenes_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)


# =============================================================================
# CORS para HTTP
# =============================================================================
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
