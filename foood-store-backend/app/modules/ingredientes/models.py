from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class Ingrediente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True)
    es_alergeno: bool = Field(default=False)
    eliminado_en: Optional[datetime] = None