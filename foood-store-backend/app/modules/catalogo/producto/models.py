from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import BigInteger, Numeric, DateTime, Column
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import Text
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

from app.modules.catalogo.shared_models import ProductoCategoria, ProductoIngrediente

if TYPE_CHECKING:
    from app.modules.catalogo.categoria.models import Categoria


class Producto(SQLModel, table=True):
    __tablename__ = "productos"

    id: Optional[int] = Field(default=None, primary_key=True, sa_type=BigInteger)
    nombre: str = Field(index=True, max_length=100)
    descripcion: Optional[str] = Field(default=None, max_length=500)
    # Array de URLs de imágenes en Cloudinary (spec v7: imagenes_url TEXT[])
    imagenes_url: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(ARRAY(Text()), nullable=True),
    )
    stock_cantidad: int = Field(default=0)
    activo: bool = Field(default=True)
    

    costo_produccion: float = Field(default=0.0, sa_type=Numeric(10, 2))
    margen_ganancia: float = Field(default=90.0, sa_type=Numeric(5, 2))
    precio: float = Field(default=0.0, sa_type=Numeric(10, 2))

    creado_en:      datetime           = Field(default_factory=_utc_now, sa_type=DateTime(timezone=True))
    actualizado_en: datetime           = Field(default_factory=_utc_now, sa_type=DateTime(timezone=True))
    eliminado_en:   Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True), nullable=True)

    categorias: List["Categoria"] = Relationship(
        back_populates="productos", link_model=ProductoCategoria
    )
    ingredientes_enlaces: List[ProductoIngrediente] = Relationship(
        back_populates="producto",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
