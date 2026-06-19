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
from typing import List, Optional

import mercadopago
from core.exceptions import NotFoundError, ForbiddenError, UnauthorizedError, BadRequestError, ConflictError, UnprocessableError, ServiceUnavailableError, BadGatewayError
from sqlmodel import Session

from core.config import settings
from app.modules.pagos.models import Pago
from app.modules.pagos.schemas import PagoResponse
from app.modules.pagos.unit_of_work import PagoUnitOfWork
from app.modules.pedido.models import Pedido, HistorialEstadoPedido
from app.modules.pedido.repository import PedidoRepository
from app.modules.pedido import stock as _stock
from app.modules.pedido.events import (
    ROOM_STAFF_PEDIDOS,
    room_user,
    serialize_pedido_estado_cambiado,
    serialize_pedido_mio_actualizado,
    serialize_stock_alerta,
)
from app.modules.pedido.schemas import PedidoPublic, HistorialEstadoPublic
from app.modules.pedido.ws_manager import ws_manager

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
        with PagoUnitOfWork(self._session) as uow:
            # 1. Buscar el pedido y validar
            pedido_repo = PedidoRepository(self._session)
            pedido = pedido_repo.get_by_id(pedido_id)
            if not pedido:
                raise NotFoundError("Pedido no encontrado")
            if pedido.usuario_id != usuario_id:
                raise ForbiddenError("No tienes permiso sobre este pedido")
            if pedido.forma_pago_codigo != "MERCADOPAGO":
                raise BadRequestError("Este pedido no usa MercadoPago")
            if pedido.estado_codigo not in ("PENDIENTE",):
                raise BadRequestError(f"El pedido está en estado {pedido.estado_codigo}, no se puede pagar")

            # 2. Verificar que no exista un pago ya creado (idempotencia por pedido)
            pago_existente = uow.pagos.get_by_pedido_id(pedido_id)
            if pago_existente and pago_existente.mp_status == "approved":
                raise BadRequestError("Este pedido ya fue pagado")
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
                    # Calcular URL publica del backend (vía ngrok) a partir de MP_NOTIFICATION_URL
                    backend_public_url = settings.MP_NOTIFICATION_URL.replace(f"{settings.API_V1_STR}/pagos/webhook", "")

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
                        # Las back_urls apuntan al BACKEND (vía ngrok), no al frontend.
                        # El backend luego redirige al frontend local.
                        "back_urls": {
                            "success": f"{backend_public_url}{settings.API_V1_STR}/pagos/redirect/success?pedido_id={pedido.id}",
                            "failure": f"{backend_public_url}{settings.API_V1_STR}/pagos/redirect/failure?pedido_id={pedido.id}",
                            "pending": f"{backend_public_url}{settings.API_V1_STR}/pagos/redirect/pending?pedido_id={pedido.id}",
                        },
                        # "auto_return": "approved",  # Comentado: MP sandbox queda atascado en error page del 3DS
                        # El usuario debe hacer click en "Volver al sitio" para regresar al backend
                    }

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

            uow.pagos.add(pago)
            response = PagoResponse.model_validate(pago)
            # UoW commitea al salir del with

        return response

    # ─────────────────────────────────────────────────────────────────────
    # 2. PROCESAR WEBHOOK (IPN de MercadoPago)
    # ─────────────────────────────────────────────────────────────────────
    async def procesar_webhook(self, data: dict) -> dict:
        """
        Recibe notificación de MercadoPago.
        Maneja dos tipos de topic:
        - topic=payment        → payment_id viene directo en data["data"]["id"]
        - topic=merchant_order → hay que consultar la merchant_order para obtener
                                  los payment_ids dentro de response["payments"]
        """
        if not self._sdk:
            logger.warning("Webhook recibido pero SDK de MP no configurado")
            return {"status": "ok", "msg": "SDK no configurado"}

        if not isinstance(data, dict):
            logger.warning(f"Webhook con data inválida: {data}")
            return {"status": "ok", "msg": "data inválida"}

        topic = data.get("topic")
        logger.info(f"[MP] Webhook recibido: topic={topic}, data_keys={list(data.keys())}")

        # ── Topic: payment directo ──────────────────────────────────────
        if topic == "payment":
            payment_id = data.get("data", {}).get("id") or data.get("id")
            if not payment_id:
                logger.warning(f"Webhook topic=payment sin payment_id: {data}")
                return {"status": "ok", "msg": "sin payment_id"}
            return await self._procesar_payment_id(payment_id)

        # ── Topic: merchant_order ──────────────────────────────────────
        if topic == "merchant_order":
            resource_url = data.get("resource")
            if not resource_url:
                logger.warning(f"Webhook topic=merchant_order sin resource: {data}")
                return {"status": "ok", "msg": "sin resource"}

            # Extraer el ID de la merchant_order desde la URL
            # resource → "https://api.mercadolibre.com/merchant_orders/12345678"
            try:
                merchant_order_id = int(resource_url.rstrip("/").split("/")[-1])
            except (ValueError, IndexError):
                logger.warning(f"No se pudo extraer merchant_order_id de: {resource_url}")
                return {"status": "ok", "msg": "merchant_order_id inválido"}

            logger.info(f"[MP] Consultando merchant_order {merchant_order_id}")
            try:
                mo_response = self._sdk.merchant_order().get(merchant_order_id)
                if mo_response.get("status") != 200:
                    logger.error(f"Error consultando merchant_order {merchant_order_id}: {mo_response}")
                    return {"status": "ok", "msg": "error consultando merchant_order"}
                merchant_order = mo_response["response"]
            except Exception as e:
                logger.error(f"Excepción consultando merchant_order {merchant_order_id}: {e}")
                return {"status": "ok", "msg": str(e)}

            # Iterar sobre todos los payments dentro de la merchant_order
            payments = merchant_order.get("payments", [])
            if not payments:
                logger.info(f"[MP] merchant_order {merchant_order_id} sin payments aún")
                return {"status": "ok", "msg": "sin payments en merchant_order"}

            logger.info(f"[MP] merchant_order {merchant_order_id} tiene {len(payments)} payment(s)")
            results = []
            for pay_info in payments:
                pid = pay_info.get("id")
                if pid:
                    r = await self._procesar_payment_id(pid)
                    results.append(r)

            return {"status": "ok", "merchant_order_id": merchant_order_id, "results": results}

        # ── Topic desconocido ──────────────────────────────────────────
        logger.info(f"[MP] Topic '{topic}' ignorado (no es payment ni merchant_order)")
        return {"status": "ok", "msg": f"topic '{topic}' no soportado"}

    async def _procesar_payment_id(self, payment_id: int) -> dict:
        """
        Consulta un payment en MP por su ID, actualiza el registro Pago
        y avanza el pedido a CONFIRMADO si corresponde.
        """
        try:
            mp_payment = self._sdk.payment().get(payment_id)
            if mp_payment.get("status") != 200:
                logger.error(f"Error consultando pago {payment_id}: {mp_payment}")
                return {"status": "ok", "msg": "error consultando MP"}

            payment_info = mp_payment["response"]
            return await self._aplicar_estado_mp(payment_info, payment_id=payment_id)
        except Exception as e:
            logger.error(f"Error en _procesar_payment_id({payment_id}): {e}", exc_info=True)
            return {"status": "ok", "msg": str(e)}

    async def _aplicar_estado_mp(
        self,
        payment_info: dict,
        payment_id: int | None = None,
    ) -> dict:
        """
        Aplica el estado de un pago de MP al registro Pago local y,
        si corresponde, avanza el pedido a CONFIRMADO.
        Se comparte entre _procesar_payment_id (webhook) y sincronizar_con_mp.

        RN-06: tras modificar el pedido, emite los eventos de WebSocket
        a la sala global de staff (pedido.estado.cambiado, stock.alerta)
        y a la sala del usuario dueño (pedido.mio.actualizado).
        """
        external_ref = payment_info.get("external_reference")
        if not external_ref:
            logger.warning(f"Pago {payment_id} sin external_reference")
            return {"status": "ok"}

        broadcast_data: dict | None = None

        with PagoUnitOfWork(self._session) as uow:
            # Buscar nuestro registro Pago
            pago = uow.pagos.get_by_external_reference(external_ref)
            if not pago:
                logger.warning(f"No se encontró Pago con external_ref={external_ref}")
                return {"status": "ok"}

            # Actualizar datos del pago
            pago.mp_payment_id = payment_info.get("id") or payment_id
            pago.mp_status = payment_info.get("status", pago.mp_status)
            pago.mp_status_detail = payment_info.get("status_detail")
            pago.transaction_amount = payment_info.get("transaction_amount", pago.transaction_amount)
            pago.payment_method_id = payment_info.get("payment_method_id")
            pago.actualizado_en = _utc_now()

            # Si fue aprobado, avanzar el pedido a CONFIRMADO solo si es DELIVERY.
            # Para EN_LOCAL el cajero debe confirmar presencialmente (validar pago en caja).
            if pago.mp_status == "approved":
                pedido_repo = PedidoRepository(self._session)
                pedido = pedido_repo.get_by_id(pago.pedido_id)
                if pedido and pedido.estado_codigo == "PENDIENTE":
                    if pedido.tipo_entrega == "DELIVERY":
                        estado_anterior = pedido.estado_codigo
                        pedido.estado_codigo = "CONFIRMADO"
                        pedido.actualizado_en = _utc_now()

                        historial = HistorialEstadoPedido(
                            pedido_id=pedido.id,
                            estado_desde=estado_anterior,
                            estado_hacia="CONFIRMADO",
                            usuario_id=None,
                            motivo="Pago aprobado por MercadoPago",
                        )
                        PedidoRepository(self._session).add_historial(historial)

                        # Descontar stock de ingredientes y detectar alertas
                        stock_bajo: Optional[List[dict]] = None
                        try:
                            cambios_stock = _stock.descontar_stock(self._session, pedido)
                            stock_bajo = _stock.detectar_stock_bajo(self._session, cambios_stock)
                        except Exception as e:
                            logger.warning(
                                f"[MP] No se pudo descontar/detectar stock para pedido {pedido.id}: {e}. "
                                "El pedido avanza a CONFIRMADO de todas formas."
                            )

                        self._session.flush()
                        self._session.refresh(pedido)
                        self._session.refresh(historial)

                        # Construir payloads para el broadcast
                        pedido_public = PedidoPublic.model_validate(pedido)
                        historial_public = HistorialEstadoPublic.model_validate(historial)
                        broadcast_data = {
                            "pedido":     pedido_public,
                            "historial":  historial_public,
                            "stock_bajo": stock_bajo,
                        }

                        logger.info(
                            f"[MP] Pedido {pedido.id} avanzar a CONFIRMADO "
                            f"(tipo_entrega=DELIVERY, payment_id={payment_id})"
                        )
                    else:
                        # EN_LOCAL: queda PENDIENTE para confirmación del cajero en el local
                        logger.info(
                            f"[MP] Pedido {pedido.id} pago aprobado pero tipo_entrega=EN_LOCAL "
                            f"→ queda PENDIENTE para confirmación del cajero"
                        )

            uow.pagos.add(pago)
            pago_id = pago.id
            mp_status = pago.mp_status
            # UoW commitea al salir del with

        # ── RN-06: Broadcast por WebSocket DESPUÉS del commit ──
        if broadcast_data:
            pedido_pub: PedidoPublic = broadcast_data["pedido"]
            historial_pub: HistorialEstadoPublic = broadcast_data["historial"]
            stock_bajo_pub: Optional[List[dict]] = broadcast_data["stock_bajo"]

            await ws_manager.broadcast(
                ROOM_STAFF_PEDIDOS,
                serialize_pedido_estado_cambiado(
                    pedido=pedido_pub,
                    estado_desde=historial_pub.estado_desde,
                    estado_hacia=historial_pub.estado_hacia,
                    usuario_actor_id=historial_pub.usuario_id,
                    motivo=historial_pub.motivo,
                    historial=historial_pub,
                ),
            )
            await ws_manager.broadcast(
                room_user(pedido_pub.usuario_id),
                serialize_pedido_mio_actualizado(
                    id_=pedido_pub.id,
                    estado_codigo=pedido_pub.estado_codigo,
                    actualizado_en=(
                        pedido_pub.actualizado_en.isoformat()
                        if pedido_pub.actualizado_en
                        else None
                    ),
                ),
            )
            if stock_bajo_pub:
                await ws_manager.broadcast(
                    ROOM_STAFF_PEDIDOS,
                    serialize_stock_alerta(stock_bajo_pub),
                )

        return {"status": "ok", "pago_id": pago_id, "mp_status": mp_status}

    # ─────────────────────────────────────────────────────────────────────
    # 3. CONSULTAR PAGO POR PEDIDO
    # ─────────────────────────────────────────────────────────────────────
    # ─────────────────────────────────────────────────────────────────────
    # 4. SINCRONIZAR CON MERCADOPAGO (Reconciliación bajo demanda)
    # ─────────────────────────────────────────────────────────────────────
    async def sincronizar_con_mp(self, pedido_id: int) -> PagoResponse:
        """
        Consulta el estado real del pago en MercadoPago y actualiza el
        registro local. Útil cuando el webhook no llegó o el cajero
        necesita verificar manualmente.

        Estrategia:
        1. Si ya tenemos mp_payment_id → sdk.payment().get(mp_payment_id)
        2. Si NO tenemos mp_payment_id pero sí external_reference
           → sdk.payment().search({"external_reference": ...})
           y se toma el primer resultado (el más reciente).
        3. Si MP no encuentra nada → mp_status="not_found", no se modifica nada.
        """
        # 1. Buscar el Pago
        pago_repo = PagoRepository(self._session)
        pago = pago_repo.get_by_pedido_id(pedido_id)
        if not pago:
            raise NotFoundError("No hay pago registrado para este pedido. "
                       "Primero hay que iniciar el pago desde MercadoPago."
            )

        if not self._sdk:
            raise ServiceUnavailableError("SDK de MercadoPago no disponible. "
                       "Verificá que MP_ACCESS_TOKEN esté configurado en el .env."
            )

        # 2. Consultar a MP
        payment_info: Optional[dict] = None

        try:
            if pago.mp_payment_id:
                # Ya tenemos el ID del payment → consulta directa
                logger.info(f"[MP] Sincronizando pago #{pago.id} con mp_payment_id={pago.mp_payment_id}")
                mp_resp = self._sdk.payment().get(pago.mp_payment_id)
                if mp_resp.get("status") == 200:
                    payment_info = mp_resp["response"]
                else:
                    logger.warning(f"[MP] payment().get({pago.mp_payment_id}) devolvió status={mp_resp.get('status')}")
                    raise BadGatewayError(f"MercadoPago no respondió para payment_id={pago.mp_payment_id}. "
                               "El pago puede haber sido eliminado o la API de MP no está disponible."
                    )

            elif pago.external_reference:
                # No tenemos payment_id → buscar por external_reference
                logger.info(f"[MP] Sincronizando pago #{pago.id} buscando por external_reference={pago.external_reference}")
                search_resp = self._sdk.payment().search({
                    "external_reference": pago.external_reference,
                    "limit": 1,
                    "sort": "date_approved",
                    "criteria": "desc",
                })
                results = search_resp.get("response", {}).get("results", [])
                if results:
                    payment_info = results[0]
                    logger.info(f"[MP] Pago encontrado en MP: id={payment_info.get('id')}, status={payment_info.get('status')}")
                else:
                    logger.warning(f"[MP] No se encontró ningún pago en MP con external_reference={pago.external_reference}")
                    # No lanzamos excepción: devolvemos el pago con mp_status="not_found"
                    with PagoUnitOfWork(self._session) as uow:
                        pago.mp_status = "not_found"
                        pago.actualizado_en = _utc_now()
                        uow.pagos.add(pago)
                        response = PagoResponse.model_validate(pago)
                    return response
            else:
                raise BadRequestError("El pago no tiene external_reference. "
                           "No se puede consultar en MercadoPago."
                )
        except (BadRequestError, BadGatewayError, NotFoundError, ServiceUnavailableError):
            raise
        except Exception as exc:
            logger.exception("[MP] Error inesperado al consultar MercadoPago: %s", exc)
            raise BadGatewayError(
                f"Error al comunicarse con MercadoPago: {exc}"
            ) from exc

        # 3. Aplicar el estado de MP al registro local
        await self._aplicar_estado_mp(payment_info)

        # 4. Devolver el pago actualizado.
        # _aplicar_estado_mp usa su propio PagoUnitOfWork que llama session.close()
        # al salir, dejando 'pago' en estado detached. Hacemos un nuevo query
        # para obtener el objeto fresco desde la sesión re-usable.
        pago_actualizado = PagoRepository(self._session).get_by_pedido_id(pedido_id)
        return PagoResponse.model_validate(pago_actualizado)

    # ─────────────────────────────────────────────────────────────────────
    # 5. CONSULTAR PAGO POR PEDIDO
    # ─────────────────────────────────────────────────────────────────────
    def obtener_pago_por_pedido(self, pedido_id: int, usuario_id: int) -> PagoResponse:
        pedido_repo = PedidoRepository(self._session)
        with PagoUnitOfWork(self._session) as uow:
            pago = uow.pagos.get_by_pedido_id(pedido_id)
            if not pago:
                raise NotFoundError("No hay pago registrado para este pedido")

            # Verificar permisos (dueño del pedido o admin)
            pedido = pedido_repo.get_by_id(pedido_id)
            if pedido and pedido.usuario_id != usuario_id:
                raise ForbiddenError("Sin permiso sobre este pago")

            return PagoResponse.model_validate(pago)
