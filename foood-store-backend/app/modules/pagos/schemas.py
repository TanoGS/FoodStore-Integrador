from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PagoCrearRequest(BaseModel):
    """Input para crear una preference de pago."""
    pedido_id: int


class PagoResponse(BaseModel):
    """Respuesta al cliente con los datos para redirigir al checkout."""
    id: int
    pedido_id: int
    mp_status: str
    mp_status_detail: Optional[str] = None
    transaction_amount: float
    payment_method_id: Optional[str] = None
    external_reference: str
    preference_id: Optional[str] = None
    init_point: Optional[str] = None
    creado_en: datetime
    actualizado_en: Optional[datetime] = None

    class Config:
        from_attributes = True


class WebhookNotification(BaseModel):
    """Payload que MercadoPago envía a /webhook (IPN)."""
    type: Optional[str] = None
    data: Optional[dict] = None
    action: Optional[str] = None
    api_version: Optional[str] = None
    date_created: Optional[str] = None
    id: Optional[int] = None
    live_mode: Optional[bool] = None
    user_id: Optional[str] = None
