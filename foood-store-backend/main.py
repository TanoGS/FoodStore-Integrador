from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings

from app.modules.categoria.router import router as categoria_router
from app.modules.ingrediente.router import router as ingrediente_router
from app.modules.producto.router import router as producto_router

from app.modules.usuario.router import router as usuarios_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], 
    allow_credentials=True,
    allow_methods=["*"],  # Permite GET, POST, PATCH, DELETE, etc.
    allow_headers=["*"],  # Permite cualquier header
)

@app.get("/")
def root():
    return {"message": "Bienvenido a la API de Food Store"}


# Rutas de categorías a la API
app.include_router(usuarios_router, prefix=settings.API_V1_STR)
app.include_router(categoria_router, prefix=settings.API_V1_STR)
app.include_router(producto_router, prefix=settings.API_V1_STR)
app.include_router(ingrediente_router, prefix=settings.API_V1_STR)

