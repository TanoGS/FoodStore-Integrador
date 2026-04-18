from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CategoriaBase(BaseModel):
    nombre: str = Field(..., max_length=100, description="Nombre único de la categoría")
    descripcion: Optional[str] = Field(None, max_length=255)
    padre_id: Optional[int] = Field(None, description="ID de la categoría padre si es una subcategoría")

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=255)
    padre_id: Optional[int] = None

class CategoriaResponse(CategoriaBase):
    id: int
    eliminado_en: Optional[datetime] = None

    class Config:
        from_attributes = True # Permite leer objetos de SQLModel