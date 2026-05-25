from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CategoriaBase(BaseModel):
    nombre: str = Field(..., max_length=50)
    descripcion: Optional[str] = Field(default=None, max_length=255)
    activo: bool = True
    parent_id: Optional[int] = None


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, max_length=50)
    descripcion: Optional[str] = Field(default=None, max_length=255)
    activo: Optional[bool] = None
    parent_id: Optional[int] = None


class CategoriaPublic(CategoriaBase):
    id: int
    creado_en:      datetime
    actualizado_en: datetime
    eliminado_en:   Optional[datetime] = None
    subcategorias: List["CategoriaPublic"] = []

    class Config:
        from_attributes = True


# Necesario para que Pydantic resuelva la auto-referencia
CategoriaPublic.model_rebuild()
