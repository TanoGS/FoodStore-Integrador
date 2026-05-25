from pydantic import BaseModel, model_validator
from typing import List, Optional
from datetime import datetime

from .models import EstadoPedido, FormaPago


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ItemPedidoCreate(BaseModel):
    producto_id: int
    cantidad:    int
    # IDs de ingredientes que el cliente desea remover (solo es_removible=true)
    personalizacion: Optional[List[int]] = None


class PedidoCreate(BaseModel):
    direccion_id:      Optional[int] = None
    forma_pago_codigo: str
    notas:             Optional[str] = None
    detalles:          List[ItemPedidoCreate]


class AvanzarEstadoRequest(BaseModel):
    estado_hacia: EstadoPedido
    motivo:       Optional[str] = None

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
    producto_id:      int
    cantidad:         int
    nombre_snapshot:  str
    precio_snapshot:  float
    subtotal_snap:    float
    personalizacion:  Optional[List[int]] = None

    class Config:
        from_attributes = True


class PedidoPublic(BaseModel):
    id:                int
    usuario_id:        int
    direccion_id:      Optional[int]
    estado_codigo:     str
    forma_pago_codigo: str
    subtotal:          float
    descuento:         float
    costo_envio:       float
    total:             float
    notas:             Optional[str]
    creado_en:         datetime
    actualizado_en:    Optional[datetime]
    detalles:          List[DetallePedidoPublic] = []

    class Config:
        from_attributes = True


class HistorialEstadoPublic(BaseModel):
    id:           int
    estado_desde: Optional[str]
    estado_hacia: str
    usuario_id:   Optional[int]
    motivo:       Optional[str]
    creado_en:    datetime

    class Config:
        from_attributes = True
