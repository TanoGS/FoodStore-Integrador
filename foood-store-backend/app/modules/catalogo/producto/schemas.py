from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime

from app.modules.catalogo.ingrediente.models import UnidadMedida
from app.modules.catalogo.categoria.schemas import CategoriaPublic


# ==============================================================================
# Schemas: Receta (relación Producto ↔ Ingrediente)
# ==============================================================================
class RecetaItemCreate(BaseModel):
    ingrediente_id: int
    cantidad_requerida: float
    es_removible: bool = True


class IngredienteBreve(BaseModel):
    id: int
    nombre: str
    unidad_medida: UnidadMedida
    es_alergeno: bool

    class Config:
        from_attributes = True


class RecetaItemPublic(BaseModel):
    ingrediente_id: int
    cantidad_requerida: float
    es_removible: bool
    ingrediente: IngredienteBreve

    class Config:
        from_attributes = True


# ==============================================================================
# Schemas: Producto
# ==============================================================================
class ProductoBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = Field(default=None, max_length=500)
    imagen_url: Optional[str] = Field(default=None, max_length=255)
    stock_cantidad: int = Field(default=0)
    activo: bool = True
    margen_ganancia: float = Field(default=90.0)


class ProductoCreate(ProductoBase):
    categoria_ids: List[int] = []
    receta: List[RecetaItemCreate] = []
    precio_manual: Optional[float] = Field(
        default=None, description="Si se envía, sobreescribe el cálculo automático"
    )
    costo_produccion_manual: Optional[float] = Field(
        default=None, description="Costo de producción manual para productos sin ingredientes"
    )


class ProductoUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, max_length=100)
    descripcion: Optional[str] = Field(default=None, max_length=500)
    imagen_url: Optional[str] = Field(default=None, max_length=255)
    stock_cantidad: Optional[int] = None
    activo: Optional[bool] = None
    margen_ganancia: Optional[float] = None
    precio_manual: Optional[float] = None
    costo_produccion_manual: Optional[float] = Field(
        default=None, description="Costo de producción manual para productos sin ingredientes"
    )
    categoria_ids: Optional[List[int]] = None
    receta: Optional[List[RecetaItemCreate]] = None


class ProductoPublic(ProductoBase):
    id: int
    costo_produccion: float
    precio: float
    creado_en:      datetime
    actualizado_en: datetime
    eliminado_en:   Optional[datetime] = None
    categorias: List[CategoriaPublic] = []
    receta_detallada: List[RecetaItemPublic] = []

    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def preparar_receta(cls, data):
        if hasattr(data, "ingredientes_enlaces"):
            enlaces = getattr(data, "ingredientes_enlaces", [])
            receta_mapeada = [
                {
                    "ingrediente_id": e.ingrediente_id,
                    "cantidad_requerida": e.cantidad_requerida,
                    "es_removible": e.es_removible,
                    "ingrediente": e.ingrediente,
                }
                for e in enlaces
                if e.ingrediente
            ]
            return {
                "id": data.id,
                "nombre": data.nombre,
                "descripcion": data.descripcion,
                "imagen_url": data.imagen_url,
                "stock_cantidad": data.stock_cantidad,
                "activo": data.activo,
                "margen_ganancia": data.margen_ganancia,
                "costo_produccion": data.costo_produccion,
                "precio": data.precio,
                "creado_en": data.creado_en,
                "actualizado_en": data.actualizado_en,
                "eliminado_en": data.eliminado_en,
                "categorias": getattr(data, "categorias", []),
                "receta_detallada": receta_mapeada,
            }
        return data


class ProductoList(BaseModel):
    data: List[ProductoPublic]
    total: int
