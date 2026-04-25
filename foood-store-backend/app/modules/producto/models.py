from typing import TYPE_CHECKING, Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
if TYPE_CHECKING:
    from app.modules.categoria.models import Categoria

# --- Tabla Intermedia Producto-Categoria ---
class ProductoCategoria(SQLModel, table=True):
    __tablename__ = "producto_categoria"
    producto_id: int = Field(foreign_key="producto.id", primary_key=True)
    categoria_id: int = Field(foreign_key="categoria.id", primary_key=True)


# --- Tabla Intermedia Producto-Ingrediente ---
class ProductoIngrediente(SQLModel, table=True):
    __tablename__ = "producto_ingrediente"
    producto_id: int = Field(foreign_key="producto.id", primary_key=True)
    ingrediente_id: int = Field(foreign_key="ingrediente.id", primary_key=True)
    es_removible: bool = Field(default=True)
    precio_adicional: float = Field(default=0.0)

# --- Modelo Principal ---
class Producto(SQLModel, table=True):
    __tablename__ = "producto"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True, unique=True, max_length=100)
    descripcion: Optional[str] = Field(default=None)
    precio_base: float = Field(default=0.0)
    es_personalizable: bool = Field(default=False)
    imagen_url: Optional[str] = Field(default=None)
    stock_disponible: int = Field(default=0)
    activo: bool = Field(default=True)
    eliminado_en: Optional[datetime] = Field(default=None)

  
    categorias: List["Categoria"] = Relationship(
        back_populates="productos", 
        link_model=ProductoCategoria
    )