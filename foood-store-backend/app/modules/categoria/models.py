from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

class Categoria(SQLModel, table=True):
  
    
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True, unique=True, max_length=100)
    descripcion: Optional[str] = Field(default=None, max_length=255)
    
    # FK autorreferencial para manejar jerarquías (subcategorías)
    padre_id: Optional[int] = Field(default=None, foreign_key="categoria.id")
    
    # Soft Delete
    eliminado_en: Optional[datetime] = Field(default=None)

    # Relaciones de SQLModel (Opcionales, pero muy útiles para ORM)
    subcategorias: List["Categoria"] = Relationship(
        back_populates="padre",
        sa_relationship_kwargs={"cascade": "all, delete"}
    )
    padre: Optional["Categoria"] = Relationship(
        back_populates="subcategorias", 
        sa_relationship_kwargs={"remote_side": "Categoria.id"}
    )