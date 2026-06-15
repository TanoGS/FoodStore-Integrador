"""
Router: Pagos
=============
Endpoints:
- POST /pagos/crear                → Crea preference MP
- POST /pagos/webhook              → Recibe IPN de MercadoPago
- GET  /pagos/redirect/success     → MP redirige acá cuando se aprueba el pago
- GET  /pagos/redirect/failure     → MP redirige acá cuando se rechaza el pago
- GET  /pagos/redirect/pending     → MP redirige acá cuando el pago está pendiente
- GET  /pagos/{pedido_id}          → Consulta estado del pago
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from core.config import settings
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


# 1. Crear preference
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


# 2. Webhook IPN (publico, sin auth)
@router.post("/webhook", status_code=200, include_in_schema=True)
async def webhook_mercadopago(
    request: Request,
    svc: PagoService = Depends(get_pago_service),
):
    """
    Webhook publico que MercadoPago llama cuando hay un cambio en un pago.
    NO requiere autenticacion (MP no puede enviar JWT).
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    result = svc.procesar_webhook(body)
    return result


# 2b. Endpoints de redireccion (MP -> backend -> frontend)
# MP redirige al backend via ngrok, y el backend redirige al frontend local.
# Esto evita necesitar 2 tuneles de ngrok (que swapean en cuenta gratuita).
@router.get("/redirect/success", include_in_schema=False)
async def redirect_success(pedido_id: int):
    """MP redirige aca cuando el pago fue aprobado."""
    frontend_base = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
    return RedirectResponse(
        url=f"{frontend_base}/pedido-exitoso/{pedido_id}?status=approved",
        status_code=302,
    )


@router.get("/redirect/failure", include_in_schema=False)
async def redirect_failure(pedido_id: int):
    """MP redirige aca cuando el pago fue rechazado."""
    frontend_base = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
    return RedirectResponse(
        url=f"{frontend_base}/pedido-exitoso/{pedido_id}?status=rejected",
        status_code=302,
    )


@router.get("/redirect/pending", include_in_schema=False)
async def redirect_pending(pedido_id: int):
    """MP redirige aca cuando el pago esta pendiente."""
    frontend_base = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
    return RedirectResponse(
        url=f"{frontend_base}/pedido-exitoso/{pedido_id}?status=pending",
        status_code=302,
    )


# 3. Consultar pago por pedido
@router.get("/{pedido_id}", response_model=PagoResponse)
def obtener_pago(
    pedido_id: int,
    svc: PagoService = Depends(get_pago_service),
    current_user: TokenData = Depends(get_current_user_token),
):
    return svc.obtener_pago_por_pedido(pedido_id, usuario_id=int(current_user.id))
