from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ProductoBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = None
    precio_base: float = Field(..., ge=0, description="El precio no puede ser negativo")
    es_personalizable: bool = False
    imagen_url: Optional[str] = None
    stock_disponible: int = Field(default=0, ge=0)
    activo: bool = True

class ProductoCreate(ProductoBase):
    categoria_ids: List[int] = Field(default=[], description="Lista de IDs de categorías asociadas")

class ProductoResponse(ProductoBase):
    id: int
    eliminado_en: Optional[datetime] = None

    class Config:
        from_attributes = True