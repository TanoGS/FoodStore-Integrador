from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class Categoria(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True)
    descripcion: Optional[str] = None
    padre_id: Optional[int] = Field(default=None, foreign_key="categoria.id")
    eliminado_en: Optional[datetime] = None