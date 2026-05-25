from fastapi import APIRouter

from .categoria.router import router as categoria_router
from .ingrediente.router import router as ingrediente_router
from .producto.router import router as producto_router

# Router maestro del dominio Catálogo.
# Cada sub-módulo registra sus propios prefijos y tags.
router = APIRouter(prefix="/catalogo")

router.include_router(categoria_router)
router.include_router(ingrediente_router)
router.include_router(producto_router)