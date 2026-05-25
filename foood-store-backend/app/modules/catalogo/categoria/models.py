from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import BigInteger, DateTime
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

from app.modules.catalogo.shared_models import ProductoCategoria

if TYPE_CHECKING:
    from app.modules.catalogo.producto.models import Producto


class Categoria(SQLModel, table=True):
    __tablename__ = "categorias"

    id: Optional[int] = Field(default=None, primary_key=True, sa_type=BigInteger)
    nombre: str = Field(unique=True, index=True, max_length=50)
    descripcion: Optional[str] = Field(default=None, max_length=255)
    activo: bool = Field(default=True)
    creado_en:      datetime           = Field(default_factory=_utc_now, sa_type=DateTime(timezone=True))
    actualizado_en: datetime           = Field(default_factory=_utc_now, sa_type=DateTime(timezone=True))
    eliminado_en:   Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True), nullable=True)

    parent_id: Optional[int] = Field(
        default=None, foreign_key="categorias.id", sa_type=BigInteger, nullable=True
    )

    parent: Optional["Categoria"] = Relationship(
        back_populates="subcategorias",
        sa_relationship_kwargs={"remote_side": "Categoria.id"},
    )
    subcategorias: List["Categoria"] = Relationship(back_populates="parent")
    productos: List["Producto"] = Relationship(
        back_populates="categorias", link_model=ProductoCategoria
    )
