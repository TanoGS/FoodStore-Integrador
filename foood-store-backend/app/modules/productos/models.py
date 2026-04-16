from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

# --- Tablas Intermedias ---
class ProductoCategoria(SQLModel, table=True):
    producto_id: Optional[int] = Field(default=None, foreign_key="producto.id", primary_key=True)
    categoria_id: Optional[int] = Field(default=None, foreign_key="categoria.id", primary_key=True)

class ProductoIngrediente(SQLModel, table=True):
    producto_id: Optional[int] = Field(default=None, foreign_key="producto.id", primary_key=True)
    ingrediente_id: Optional[int] = Field(default=None, foreign_key="ingrediente.id", primary_key=True)

# --- Tabla Principal ---
class Producto(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True)
    descripcion: str
    precio: float = Field(default=0.0) # Luego manejaremos precisión exacta si es necesario
    stock: int = Field(default=0)
    disponible: bool = Field(default=True)
    eliminado_en: Optional[datetime] = None