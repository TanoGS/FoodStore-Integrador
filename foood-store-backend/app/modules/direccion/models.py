from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger, DateTime
from datetime import datetime, timezone


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DireccionEntrega(SQLModel, table=True):
    __tablename__ = "direcciones_entrega"

    id:         Optional[int] = Field(default=None, primary_key=True, sa_type=BigInteger)
    usuario_id: int           = Field(foreign_key="usuarios.id", sa_type=BigInteger)

    alias:        Optional[str] = Field(default=None, max_length=50)
    calle:        str           = Field(max_length=100)
    numero:       str           = Field(max_length=20)
    piso:         Optional[str] = Field(default=None, max_length=10)
    departamento: Optional[str] = Field(default=None, max_length=10)
    ciudad:       str           = Field(max_length=100)
    codigo_postal: str          = Field(max_length=20)
    predeterminada: bool        = Field(default=False)

    creado_en:      datetime           = Field(default_factory=_utc_now, sa_type=DateTime(timezone=True))
    actualizado_en: datetime           = Field(default_factory=_utc_now, sa_type=DateTime(timezone=True))
    eliminado_en:   Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True), nullable=True)