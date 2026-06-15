from pydantic import BaseModel, model_validator, field_validator
from typing import List, Optional
from datetime import datetime

from .models import EstadoPedido, FormaPago, TipoEntrega


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

_TIPO_ENTREGA_LABELS: dict[str, str] = {
    "EN_LOCAL": "En el local",
    "DELIVERY": "Delivery",
}


class ItemPedidoCreate(BaseModel):
    producto_id: int
    cantidad: int
    # IDs de ingredientes que el cliente desea remover (solo es_removible=true)
    personalizacion: Optional[List[int]] = None


class PedidoCreate(BaseModel):
    direccion_id: Optional[int] = None
    forma_pago_codigo: str
    tipo_entrega: TipoEntrega = TipoEntrega.DELIVERY
    notas: Optional[str] = None
    detalles: List[ItemPedidoCreate]

    @field_validator("tipo_entrega", mode="before")
    @classmethod
    def coerce_tipo_entrega(cls, v):
        if isinstance(v, str):
            try:
                return TipoEntrega(v)
            except ValueError:
                raise ValueError(f"tipo_entrega inválido: {v}")
        return v

    @model_validator(mode="after")
    def validar_delivery(self) -> "PedidoCreate":
        if self.tipo_entrega == TipoEntrega.DELIVERY:
            if self.direccion_id is None:
                raise ValueError("La dirección es obligatoria para delivery.")
            if self.forma_pago_codigo != "MERCADOPAGO":
                raise ValueError("Solo se acepta MercadoPago para delivery.")
        return self


class AvanzarEstadoRequest(BaseModel):
    estado_hacia: EstadoPedido
    motivo: Optional[str] = None

    @model_validator(mode="after")
    def motivo_requerido_si_cancela(self) -> "AvanzarEstadoRequest":
        if self.estado_hacia == EstadoPedido.CANCELADO and not self.motivo:
            raise ValueError("El motivo es obligatorio al cancelar un pedido.")
        return self


class CancelarPedidoRequest(BaseModel):
    motivo: str


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class DetallePedidoPublic(BaseModel):
    producto_id: int
    cantidad: int
    nombre_snapshot: str
    precio_snapshot: float
    subtotal_snap: float
    personalizacion: Optional[List[int]] = None
    personalizacion_nombres: Optional[List[str]] = None

    class Config:
        from_attributes = True


class PedidoPublic(BaseModel):
    id: int
    usuario_id: int
    direccion_id: Optional[int]
    estado_codigo: str
    forma_pago_codigo: str
    tipo_entrega: str
    subtotal: float
    descuento: float
    costo_envio: float
    total: float
    notas: Optional[str]
    creado_en: datetime
    actualizado_en: Optional[datetime]
    detalles: List[DetallePedidoPublic] = []

    class Config:
        from_attributes = True


class HistorialEstadoPublic(BaseModel):
    id: int
    estado_desde: Optional[str]
    estado_hacia: str
    usuario_id: Optional[int]
    motivo: Optional[str]
    creado_en: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Direcciones resumidas (para enriquecer pedido en vistas de staff)
# ---------------------------------------------------------------------------

class DireccionResumida(BaseModel):
    calle:      Optional[str] = None
    numero:     Optional[str] = None
    ciudad:     Optional[str] = None
    referencia: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Colección: PedidoAdmin — enriquecido para staff
# ---------------------------------------------------------------------------

class PedidoList(BaseModel):
    """Schema para respuestas paginadas de pedidos."""
    data: List[PedidoPublic]
    total: int


class PedidoAdminList(BaseModel):
    """Schema para respuestas paginadas de pedidos enriquecidos (staff)."""
    data: List["PedidoAdmin"]
    total: int


class PedidoAdmin(BaseModel):
    """
    Schema enriquecido para vistas administrativas (GestorPedidos).
    Incluye datos expandidos del usuario, dirección y forma de pago
    que en PedidoPublic solo vienen como IDs.
    """
    id:                  int
    usuario_id:          int
    usuario_nombre:       str
    usuario_email:       str
    direccion_id:        Optional[int] = None
    direccion:           Optional[DireccionResumida] = None
    estado_codigo:        str
    forma_pago_codigo:    str
    forma_pago_label:     str
    tipo_entrega:         str
    tipo_entrega_label:   str
    subtotal:            float
    descuento:            float
    costo_envio:         float
    total:               float
    notas:                Optional[str] = None
    creado_en:            datetime
    actualizado_en:       Optional[datetime] = None
    detalles:            List[DetallePedidoPublic] = []

    class Config:
        from_attributes = True
