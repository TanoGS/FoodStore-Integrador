from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings

from app.modules.usuario.router import router as usuarios_router
from app.modules.pedido.router import router as pedido_router
from app.modules.direccion.router import router as direccion_router
from app.modules.catalogo.router import router as catalogo_router  # El nuevo router maestro

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)


# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], 
    allow_credentials=True, # Indispensable en True para que el navegador acepte las cookies HttpOnly
    allow_methods=["*"],  
    allow_headers=["*"],  
)

@app.get("/")
def root():
    return {"message": "Bienvenido a la API de Food Store"}


# Rutas activas de la API (con el prefijo de tus configuraciones globales)
app.include_router(usuarios_router, prefix=settings.API_V1_STR)
app.include_router(pedido_router, prefix=settings.API_V1_STR)
app.include_router(direccion_router, prefix=settings.API_V1_STR)
app.include_router(catalogo_router, prefix=settings.API_V1_STR)