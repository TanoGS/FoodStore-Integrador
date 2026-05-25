from enum import Enum
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import BigInteger, Numeric, DateTime, String
from typing import Optional, List
from datetime import datetime, timezone


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

from app.modules.catalogo.shared_models import ProductoIngrediente


class UnidadMedida(str, Enum):
    UNIDAD = "UNIDAD"
    KILOGRAMO = "KILOGRAMO"
    LITRO = "LITRO"


# ==============================================================================
# Ingrediente (insumo base de cocina con costo y stock)
# ==============================================================================
class Ingrediente(SQLModel, table=True):
    __tablename__ = "ingrediente"

    id: Optional[int] = Field(default=None, primary_key=True, sa_type=BigInteger)
    nombre: str = Field(unique=True, index=True, max_length=50)
    stock: float = Field(default=0.0, sa_type=Numeric(10, 3))
    stock_seguridad: float = Field(default=0.0, sa_type=Numeric(10, 3))
    unidad_medida: UnidadMedida = Field(sa_type=String(20))
    es_alergeno: bool = Field(default=False)
    costo_unitario: float = Field(default=0.0, sa_type=Numeric(10, 2))
    creado_en:      datetime           = Field(default_factory=_utc_now, sa_type=DateTime(timezone=True))
    actualizado_en: datetime           = Field(default_factory=_utc_now, sa_type=DateTime(timezone=True))
    eliminado_en:   Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True), nullable=True)

    productos_enlaces: List[ProductoIngrediente] = Relationship(
        back_populates="ingrediente"
    )
