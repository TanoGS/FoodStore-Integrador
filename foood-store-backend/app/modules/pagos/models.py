"""
Modelo: Pago
============
Registra cada intento de cobro a través de MercadoPago.
Se vincula 1-a-1 con un Pedido vía external_reference (UUID).
"""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Numeric, BigInteger, DateTime


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Pago(SQLModel, table=True):
    __tablename__ = "pagos"

    id: Optional[int] = Field(default=None, primary_key=True, sa_type=BigInteger)

    # FK a pedidos
    pedido_id: int = Field(foreign_key="pedidos.id", sa_type=BigInteger, index=True)

    # Datos devueltos por MercadoPago
    mp_payment_id:     Optional[int]    = Field(default=None, sa_type=BigInteger, index=True)
    mp_status:         str              = Field(default="pending", max_length=30)
    mp_status_detail:  Optional[str]    = Field(default=None, max_length=100)
    transaction_amount: float           = Field(default=0.0, sa_type=Numeric(10, 2))
    payment_method_id: Optional[str]    = Field(default=None, max_length=50)

    # Identificadores únicos para idempotencia
    external_reference: str             = Field(max_length=100, unique=True, index=True)
    idempotency_key:    str             = Field(max_length=100, unique=True, index=True)

    # Datos opcionales del preference (Checkout PRO)
    preference_id:      Optional[str]   = Field(default=None, max_length=100)
    init_point:         Optional[str]   = Field(default=None, max_length=500)

    # Auditoría
    creado_en:      datetime           = Field(default_factory=_utc_now, sa_type=DateTime(timezone=True))
    actualizado_en: Optional[datetime] = Field(default=None,    sa_type=DateTime(timezone=True))
