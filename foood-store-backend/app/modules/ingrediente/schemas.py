from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class IngredienteBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    es_alergeno: bool = False

class IngredienteCreate(IngredienteBase):
    pass

class IngredienteUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    es_alergeno: Optional[bool] = None

class IngredienteResponse(IngredienteBase):
    id: int
    eliminado_en: Optional[datetime] = None

    class Config:
        from_attributes = True