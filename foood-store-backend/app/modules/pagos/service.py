"""
Servicio: PagoService
=====================
Encapsula la lógica de integración con MercadoPago.
- Crea preferences de Checkout PRO
- Procesa webhooks (IPN)
- Consulta estado de pagos
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

import mercadopago
from fastapi import HTTPException
from sqlmodel import Session, select

from core.config import settings
from app.modules.pagos.models import Pago
from app.modules.pagos.schemas import PagoResponse
from app.modules.pedido.models import Pedido, HistorialEstadoPedido

logger = logging.getLogger("pagos")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PagoService:
    def __init__(self, session: Session) -> None:
        self._session = session
        # SDK de MercadoPago - inicializado con el access token del .env
        try:
            self._sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)
        except Exception as e:
            logger.warning(f"No se pudo inicializar SDK de MercadoPago: {e}")
            self._sdk = None

    # ─────────────────────────────────────────────────────────────────────
    # 1. CREAR PAGO (Preference Checkout PRO)
    # ─────────────────────────────────────────────────────────────────────
    def crear_pago(self, pedido_id: int, usuario_id: int) -> PagoResponse:
        """
        Crea una preference de pago en MercadoPago para un pedido.
        - Genera external_reference (UUID) e idempotency_key únicos
        - Devuelve el init_point al que debe redirigir el frontend
        """
        # 1. Buscar el pedido y validar
        pedido = self._session.get(Pedido, pedido_id)
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        if pedido.usuario_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tienes permiso sobre este pedido")
        if pedido.forma_pago_codigo != "MERCADOPAGO":
            raise HTTPException(status_code=400, detail="Este pedido no usa MercadoPago")
        if pedido.estado_codigo not in ("PENDIENTE",):
            raise HTTPException(status_code=400, detail=f"El pedido está en estado {pedido.estado_codigo}, no se puede pagar")

        # 2. Verificar que no exista un pago ya creado (idempotencia por pedido)
        pago_existente = self._session.exec(
            select(Pago).where(Pago.pedido_id == pedido_id)
        ).first()
        if pago_existente and pago_existente.mp_status == "approved":
            raise HTTPException(status_code=400, detail="Este pedido ya fue pagado")
        if pago_existente and pago_existente.init_point and pago_existente.mp_status == "pending":
            # Reutilizar preference existente si aún está pendiente
            return PagoResponse.model_validate(pago_existente)

        # 3. Crear el registro Pago
        external_ref = str(uuid.uuid4())
        idemp_key = str(uuid.uuid4())
        pago = Pago(
            pedido_id=pedido_id,
            transaction_amount=float(pedido.total),
            external_reference=external_ref,
            idempotency_key=idemp_key,
            mp_status="pending",
        )

        # 4. Crear la preference en MP (si hay SDK configurado)
        if self._sdk:
            try:
                # Construir URLs de retorno usando FRONTEND_URL del settings
                frontend_base = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
                pedido_url = f"{frontend_base}/pedido-exitoso/{pedido.id}"
                
                logger.info(f"[MP] FRONTEND_URL={frontend_base}, constructing back_urls...")
                
                preference_data = {
                    "items": [
                        {
                            "id": str(pedido.id),
                            "title": f"Pedido #{pedido.id} - FoodStore",
                            "quantity": 1,
                            "currency_id": "ARS",
                            "unit_price": float(pedido.total),
                        }
                    ],
                    "external_reference": external_ref,
                    "notification_url": settings.MP_NOTIFICATION_URL,
                    "back_urls": {
                        "success": f"{pedido_url}?status=approved",
                        "failure": f"{pedido_url}?status=rejected",
                        "pending": f"{pedido_url}?status=pending",
                    },
                    # NOTA: No usamos auto_return porque requiere back_urls en ciertos contextos
                    # El frontend maneja la redirección después del pago
                }
                
                logger.info(f"[MP] Creating preference with data: {preference_data}")
                
                result = self._sdk.preference().create(preference_data)
                status = result.get("status")
                
                if status in (200, 201):
                    pref = result["response"]
                    pago.preference_id = pref.get("id")
                    # sandbox_init_point en TEST, init_point en PROD
                    pago.init_point = (
                        pref.get("sandbox_init_point")
                        or pref.get("init_point")
                    )
                    logger.info(f"[MP] Preference created! init_point={pago.init_point}")
                else:
                    logger.error(f"MP preference error: status={status}, response={result.get('response')}")
            except Exception as e:
                logger.error(f"Error creando preference: {e}", exc_info=True)
                # Continuar sin init_point: el cliente puede consultar manualmente

        self._session.add(pago)
        self._session.commit()
        self._session.refresh(pago)
        return PagoResponse.model_validate(pago)

    # ─────────────────────────────────────────────────────────────────────
    # 2. PROCESAR WEBHOOK (IPN de MercadoPago)
    # ─────────────────────────────────────────────────────────────────────
    def procesar_webhook(self, data: dict) -> dict:
        """
        Recibe notificación de MercadoPago (topic=payment).
        Consulta el pago, actualiza el estado y avanza el pedido.
        """
        if not self._sdk:
            logger.warning("Webhook recibido pero SDK de MP no configurado")
            return {"status": "ok", "msg": "SDK no configurado"}

        # Extraer payment_id del payload
        payment_id = None
        if isinstance(data, dict):
            if "data" in data and isinstance(data["data"], dict):
                payment_id = data["data"].get("id")
            elif "id" in data:
                payment_id = data["id"]

        if not payment_id:
            logger.warning(f"Webhook sin payment_id: {data}")
            return {"status": "ok", "msg": "sin payment_id"}

        # Consultar el pago en MP
        try:
            mp_payment = self._sdk.payment().get(payment_id)
            if mp_payment.get("status") != 200:
                logger.error(f"Error consultando pago {payment_id}: {mp_payment}")
                return {"status": "ok", "msg": "error consultando MP"}

            payment_info = mp_payment["response"]
            external_ref = payment_info.get("external_reference")
            if not external_ref:
                logger.warning(f"Pago {payment_id} sin external_reference")
                return {"status": "ok"}

            # Buscar nuestro registro Pago
            pago = self._session.exec(
                select(Pago).where(Pago.external_reference == external_ref)
            ).first()
            if not pago:
                logger.warning(f"No se encontró Pago con external_ref={external_ref}")
                return {"status": "ok"}

            # Actualizar datos del pago
            pago.mp_payment_id = payment_info.get("id")
            pago.mp_status = payment_info.get("status", pago.mp_status)
            pago.mp_status_detail = payment_info.get("status_detail")
            pago.transaction_amount = payment_info.get("transaction_amount", pago.transaction_amount)
            pago.payment_method_id = payment_info.get("payment_method_id")
            pago.actualizado_en = _utc_now()

            # Si fue aprobado, avanzar el pedido a CONFIRMADO
            if pago.mp_status == "approved":
                pedido = self._session.get(Pedido, pago.pedido_id)
                if pedido and pedido.estado_codigo == "PENDIENTE":
                    estado_anterior = pedido.estado_codigo
                    pedido.estado_codigo = "CONFIRMADO"
                    pedido.actualizado_en = _utc_now()

                    # Insertar historial (append-only)
                    historial = HistorialEstadoPedido(
                        pedido_id=pedido.id,
                        estado_desde=estado_anterior,
                        estado_hacia="CONFIRMADO",
                        usuario_id=None,  # NULL = sistema (webhook)
                        motivo="Pago aprobado por MercadoPago",
                    )
                    self._session.add(historial)

            self._session.add(pago)
            self._session.commit()

            return {"status": "ok", "pago_id": pago.id, "mp_status": pago.mp_status}
        except Exception as e:
            logger.error(f"Error procesando webhook: {e}")
            return {"status": "ok", "msg": str(e)}

    # ─────────────────────────────────────────────────────────────────────
    # 3. CONSULTAR PAGO POR PEDIDO
    # ─────────────────────────────────────────────────────────────────────
    def obtener_pago_por_pedido(self, pedido_id: int, usuario_id: int) -> PagoResponse:
        pago = self._session.exec(
            select(Pago).where(Pago.pedido_id == pedido_id)
        ).first()
        if not pago:
            raise HTTPException(status_code=404, detail="No hay pago registrado para este pedido")

        # Verificar permisos (dueño del pedido o admin)
        pedido = self._session.get(Pedido, pedido_id)
        if pedido and pedido.usuario_id != usuario_id:
            raise HTTPException(status_code=403, detail="Sin permiso sobre este pago")

        return PagoResponse.model_validate(pago)
