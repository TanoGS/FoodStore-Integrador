from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class Ingrediente(SQLModel, table=True):
    __tablename__ = "ingrediente"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True, unique=True, max_length=100)
    es_alergeno: bool = Field(default=False)
    
    # Soft Delete
    eliminado_en: Optional[datetime] = Field(default=None)