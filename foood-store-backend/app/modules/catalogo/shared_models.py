from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import BigInteger, Numeric
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.catalogo.producto.models import Producto
    from app.modules.catalogo.ingrediente.models import Ingrediente


# ==============================================================================
# TABLAS ASOCIATIVAS (sin lógica de negocio propia)
# Los string-refs de Relationship son resueltos por el registro de SQLAlchemy
# en el primer evento de configuración del mapper (antes de cualquier query).
# ==============================================================================

class ProductoCategoria(SQLModel, table=True):
    __tablename__ = "productos_categorias"

    producto_id: int = Field(
        default=None, foreign_key="productos.id", primary_key=True, sa_type=BigInteger
    )
    categoria_id: int = Field(
        default=None, foreign_key="categorias.id", primary_key=True, sa_type=BigInteger
    )


class ProductoIngrediente(SQLModel, table=True):
    __tablename__ = "productos_ingredientes"

    producto_id: int = Field(
        default=None, foreign_key="productos.id", primary_key=True, sa_type=BigInteger
    )
    ingrediente_id: int = Field(
        default=None, foreign_key="ingrediente.id", primary_key=True, sa_type=BigInteger
    )
    cantidad_requerida: float = Field(sa_type=Numeric(10, 3))
    es_removible: bool = Field(default=True)

    producto: "Producto" = Relationship(back_populates="ingredientes_enlaces")
    ingrediente: "Ingrediente" = Relationship(back_populates="productos_enlaces")
