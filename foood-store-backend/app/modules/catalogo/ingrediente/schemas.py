from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .models import UnidadMedida


# ==============================================================================
# Schemas: Ingrediente (Materia Prima)
# ==============================================================================
class IngredienteBase(BaseModel):
    nombre: str = Field(..., max_length=50)
    stock: float = Field(default=0.0)
    stock_seguridad: float = Field(default=0.0)
    unidad_medida: UnidadMedida
    es_alergeno: bool = False
    costo_unitario: float = Field(..., description="Costo por unidad de medida base")


class IngredienteCreate(IngredienteBase):
    pass


class IngredienteUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, max_length=50)
    stock: Optional[float] = None
    stock_seguridad: Optional[float] = None
    unidad_medida: Optional[UnidadMedida] = None
    es_alergeno: Optional[bool] = None
    costo_unitario: Optional[float] = None


class IngredientePublic(IngredienteBase):
    id: int
    creado_en:      datetime
    actualizado_en: datetime
    eliminado_en:   Optional[datetime] = None

    class Config:
        from_attributes = True


class IngredienteList(BaseModel):
    data: list[IngredientePublic]
    total: int
