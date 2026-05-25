import enum
from datetime import datetime, timezone
from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import BigInteger, Numeric, DateTime, Column
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import Integer


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enums de dominio (FSM y Formas de Pago)
# ---------------------------------------------------------------------------

class EstadoPedido(str, enum.Enum):
    PENDIENTE      = "PENDIENTE"
    CONFIRMADO     = "CONFIRMADO"
    EN_PREPARACION = "EN_PREPARACION"
    EN_CAMINO      = "EN_CAMINO"
    ENTREGADO      = "ENTREGADO"
    CANCELADO      = "CANCELADO"


class FormaPago(str, enum.Enum):
    EFECTIVO      = "EFECTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"
    MERCADOPAGO   = "MERCADOPAGO"


# ---------------------------------------------------------------------------
# Tabla: pedidos
# ---------------------------------------------------------------------------

class Pedido(SQLModel, table=True):
    __tablename__ = "pedidos"

    id: Optional[int] = Field(default=None, primary_key=True, sa_type=BigInteger)

    # FK → usuarios (NN)
    usuario_id: int = Field(foreign_key="usuarios.id", sa_type=BigInteger)
    # FK → direcciones_entrega (SET NULL permitido)
    direccion_id: Optional[int] = Field(
        default=None, foreign_key="direcciones_entrega.id",
        sa_type=BigInteger, nullable=True
    )

    # Estado como VARCHAR para ser FK-like hacia el catálogo semántico
    estado_codigo: str = Field(
        default=EstadoPedido.PENDIENTE,
        max_length=20
    )
    forma_pago_codigo: str = Field(max_length=20)

    # Snapshot monetario inmutable desde creación
    subtotal:     float = Field(default=0.0, sa_type=Numeric(10, 2))
    descuento:    float = Field(default=0.0, sa_type=Numeric(10, 2))
    costo_envio:  float = Field(default=50.0, sa_type=Numeric(10, 2))
    total:        float = Field(default=0.0, sa_type=Numeric(10, 2))

    notas: Optional[str] = Field(default=None)

    creado_en:      datetime           = Field(default_factory=_utc_now, sa_type=DateTime(timezone=True))
    actualizado_en: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))

    # Relaciones
    detalles:  List["DetallePedido"]         = Relationship(back_populates="pedido")
    historial: List["HistorialEstadoPedido"] = Relationship(back_populates="pedido")


# ---------------------------------------------------------------------------
# Tabla: detalles_pedido  (Snapshot Pattern — fila inmutable)
# ---------------------------------------------------------------------------

class DetallePedido(SQLModel, table=True):
    __tablename__ = "detalles_pedido"

    # PK compuesta (pedido_id, producto_id)
    pedido_id:   int = Field(foreign_key="pedidos.id",   primary_key=True, sa_type=BigInteger)
    producto_id: int = Field(foreign_key="productos.id", primary_key=True, sa_type=BigInteger)

    cantidad: int = Field(ge=1)

    # Snapshot inmutable — se registran en el momento de la compra
    nombre_snapshot:  str   = Field(max_length=200)
    precio_snapshot:  float = Field(sa_type=Numeric(10, 2))
    subtotal_snap:    float = Field(sa_type=Numeric(10, 2))

    # IDs de ingredientes removidos por el cliente (solo es_removible=true)
    personalizacion: Optional[List[int]] = Field(
        default=None,
        sa_column=Column(ARRAY(Integer), nullable=True)
    )

    creado_en: datetime = Field(default_factory=_utc_now, sa_type=DateTime(timezone=True))

    # Relación
    pedido: Optional[Pedido] = Relationship(back_populates="detalles")


# ---------------------------------------------------------------------------
# Tabla: historial_estados_pedido  (Audit Trail — APPEND-ONLY, jamás UPDATE/DELETE)
# ---------------------------------------------------------------------------

class HistorialEstadoPedido(SQLModel, table=True):
    __tablename__ = "historial_estados_pedido"

    id: Optional[int] = Field(default=None, primary_key=True, sa_type=BigInteger)

    pedido_id: int = Field(foreign_key="pedidos.id", sa_type=BigInteger)

    # NULL en la primera entrada (RN-02: creación del pedido)
    estado_desde: Optional[str] = Field(default=None, max_length=20, nullable=True)
    estado_hacia: str            = Field(max_length=20)

    # NULL cuando el actor es el sistema (webhook)
    usuario_id: Optional[int] = Field(
        default=None, foreign_key="usuarios.id",
        sa_type=BigInteger, nullable=True
    )
    motivo: Optional[str] = Field(default=None)

    # Solo INSERT — campo de auditoría append-only
    creado_en: datetime = Field(default_factory=_utc_now, sa_type=DateTime(timezone=True))

    # Relación
    pedido: Optional[Pedido] = Relationship(back_populates="historial")