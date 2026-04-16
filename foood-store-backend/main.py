from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings

from app.modules.categorias.router import router as categorias_router

from app.modules.usuarios.router import router as usuarios_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Bienvenido a la API de Food Store"}


# Conectamos las rutas de categorías a la API
app.include_router(categorias_router, prefix=settings.API_V1_STR)
app.include_router(usuarios_router, prefix=settings.API_V1_STR)
