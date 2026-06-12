"""
Router: Pagos
=============
Endpoints:
- POST /pagos/crear           → Crea preference MP
- POST /pagos/webhook         → Recibe IPN de MercadoPago
- GET  /pagos/{pedido_id}     → Consulta estado del pago
"""
from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from core.database import get_session
from core.security import RoleChecker, get_current_user_token, TokenData
from app.modules.pagos.service import PagoService
from app.modules.pagos.schemas import PagoCrearRequest, PagoResponse, WebhookNotification

router = APIRouter(
    prefix="/pagos",
    tags=["Pagos — MercadoPago"],
)


def get_pago_service(session: Session = Depends(get_session)) -> PagoService:
    return PagoService(session)


# ── 1. Crear preference ──────────────────────────────────────────────────
@router.post("/crear", response_model=PagoResponse, status_code=201)
def crear_pago(
    body: PagoCrearRequest,
    svc: PagoService = Depends(get_pago_service),
    current_user: TokenData = Depends(get_current_user_token),
):
    """
    Crea una preference de MercadoPago para el pedido indicado.
    Devuelve el `init_point` al que el frontend debe redirigir al cliente.
    """
    return svc.crear_pago(body.pedido_id, usuario_id=int(current_user.id))


# ── 2. Webhook IPN (público, sin auth) ───────────────────────────────────
@router.post("/webhook", status_code=200, include_in_schema=True)
async def webhook_mercadopago(
    request: Request,
    svc: PagoService = Depends(get_pago_service),
):
    """
    Webhook público que MercadoPago llama cuando hay un cambio en un pago.
    NO requiere autenticación (MP no puede enviar JWT).
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    result = svc.procesar_webhook(body)
    return result


# ── 3. Consultar pago por pedido ─────────────────────────────────────────
@router.get("/{pedido_id}", response_model=PagoResponse)
def obtener_pago(
    pedido_id: int,
    svc: PagoService = Depends(get_pago_service),
    current_user: TokenData = Depends(get_current_user_token),
):
    return svc.obtener_pago_por_pedido(pedido_id, usuario_id=int(current_user.id))
