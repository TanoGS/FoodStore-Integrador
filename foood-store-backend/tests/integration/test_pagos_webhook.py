"""
test_pagos_webhook.py — Tests de integración del webhook de MercadoPago.
========================================================================
Endpoint cubierto:
- POST /api/pedidos/{id}/estado  → avanzar/cancelar pedido

Reglas de negocio probadas:
- DELIVERY + mp_status=approved → avanza a CONFIRMADO
- EN_LOCAL + mp_status=approved → queda PENDIENTE (cajero confirma)
- topic=merchant_order → procesa todos los payments
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.integration
class TestPagosWebhook:
    """Tests de webhook de MercadoPago."""

    @patch("app.modules.pagos.service.mercadopago.SDK")
    def test_webhook_payment_approved_delivery_avanza_a_confirmado(
        self, mock_sdk_class, client, test_user, test_producto, test_direccion, db_session
    ):
        """DELIVERY + payment approved debe avanzar a CONFIRMADO."""
        from tests.conftest import auth_headers

        headers = auth_headers(test_user, db_session)

        # Crear pedido DELIVERY con MP
        create_resp = client.post(
            "/api/pedidos/",
            headers=headers,
            json={
                "tipo_entrega": "DELIVERY",
                "direccion_id": test_direccion.id,
                "forma_pago_codigo": "MERCADOPAGO",
                "detalles": [{"producto_id": test_producto.id, "cantidad": 1}],
            },
        )
        assert create_resp.status_code == 201
        pedido_id = create_resp.json()["id"]

        # Simular webhook: DELIVERY + payment approved
        mock_sdk = MagicMock()
        mock_sdk.payment().get.return_value = {
            "status": 200,
            "response": {
                "id": 999999,
                "status": "approved",
                "external_reference": db_session.query(
                    __import__("app.modules.pagos.models", fromlist=["Pago"]).Pago
                ).filter_by(pedido_id=pedido_id).first().external_reference,
                "transaction_amount": 1500.0,
                "payment_method_id": "visa",
            },
        }
        mock_sdk_class.return_value = mock_sdk

        # Crear el pago en BD para tener external_reference
        from app.modules.pagos.models import Pago
        from app.modules.pagos.service import PagoService

        svc = PagoService(db_session)
        pago_resp = svc.crear_pago(pedido_id=pedido_id, usuario_id=test_user.id)
        ext_ref = pago_resp.external_reference

        # Simular webhook
        response = client.post(
            "/api/pagos/webhook",
            json={"topic": "payment", "data": {"id": 999999}},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # Verificar que el pedido avanzó a CONFIRMADO
        db_session.expire_all()
        pedido_actualizado = client.get(f"/api/pedidos/{pedido_id}", headers=headers)
        assert pedido_actualizado.json()["estado_codigo"] == "CONFIRMADO"

    @patch("app.modules.pagos.service.mercadopago.SDK")
    def test_webhook_payment_approved_enlocal_queda_pendiente(
        self, mock_sdk_class, client, test_user, test_producto, db_session
    ):
        """EN_LOCAL + payment approved debe QUEDAR PENDIENTE (cajero confirma)."""
        from tests.conftest import auth_headers

        headers = auth_headers(test_user, db_session)

        # Crear pedido EN_LOCAL con MP
        create_resp = client.post(
            "/api/pedidos/",
            headers=headers,
            json={
                "tipo_entrega": "EN_LOCAL",
                "forma_pago_codigo": "MERCADOPAGO",
                "detalles": [{"producto_id": test_producto.id, "cantidad": 1}],
            },
        )
        assert create_resp.status_code == 201
        pedido_id = create_resp.json()["id"]

        # Crear pago para tener external_reference
        from app.modules.pagos.service import PagoService
        svc = PagoService(db_session)
        pago_resp = svc.crear_pago(pedido_id=pedido_id, usuario_id=test_user.id)
        ext_ref = pago_resp.external_reference

        # Mock del SDK
        mock_sdk = MagicMock()
        mock_sdk.payment().get.return_value = {
            "status": 200,
            "response": {
                "id": 888888,
                "status": "approved",
                "external_reference": ext_ref,
                "transaction_amount": 1500.0,
                "payment_method_id": "visa",
            },
        }
        mock_sdk_class.return_value = mock_sdk

        # Webhook
        response = client.post(
            "/api/pagos/webhook",
            json={"topic": "payment", "data": {"id": 888888}},
        )
        assert response.status_code == 200

        # Verificar que quedó PENDIENTE (no avanzó a CONFIRMADO)
        db_session.expire_all()
        pedido_actualizado = client.get(f"/api/pedidos/{pedido_id}", headers=headers)
        assert pedido_actualizado.json()["estado_codigo"] == "PENDIENTE"

    @patch("app.modules.pagos.service.mercadopago.SDK")
    def test_webhook_topic_merchant_order_procesa_todos_los_payments(
        self, mock_sdk_class, client, test_user, test_producto, test_direccion, db_session
    ):
        """topic=merchant_order debe procesar todos los payments dentro de la order."""
        from tests.conftest import auth_headers

        headers = auth_headers(test_user, db_session)

        # Crear pedido DELIVERY con MP
        create_resp = client.post(
            "/api/pedidos/",
            headers=headers,
            json={
                "tipo_entrega": "DELIVERY",
                "direccion_id": test_direccion.id,
                "forma_pago_codigo": "MERCADOPAGO",
                "detalles": [{"producto_id": test_producto.id, "cantidad": 1}],
            },
        )
        assert create_resp.status_code == 201
        pedido_id = create_resp.json()["id"]

        # Crear pago
        from app.modules.pagos.service import PagoService
        svc = PagoService(db_session)
        pago_resp = svc.crear_pago(pedido_id=pedido_id, usuario_id=test_user.id)
        ext_ref = pago_resp.external_reference

        # Mock del SDK para merchant_order
        mock_sdk = MagicMock()
        mock_sdk.merchant_order().get.return_value = {
            "status": 200,
            "response": {
                "id": 777777,
                "payments": [
                    {"id": 111111, "status": "approved"},
                    {"id": 222222, "status": "pending"},
                ],
            },
        }
        mock_sdk.payment().get.return_value = {
            "status": 200,
            "response": {
                "id": 111111,
                "status": "approved",
                "external_reference": ext_ref,
                "transaction_amount": 1500.0,
                "payment_method_id": "visa",
            },
        }
        mock_sdk_class.return_value = mock_sdk

        # Webhook con topic=merchant_order
        response = client.post(
            "/api/pagos/webhook",
            json={
                "topic": "merchant_order",
                "resource": "https://api.mercadolibre.com/merchant_orders/777777",
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "ok"
        assert result["merchant_order_id"] == 777777

    def test_webhook_sin_sdk_devuelve_ok(self, client):
        """Webhook sin SDK configurado debe devolver {'status': 'ok'} sin romper."""
        response = client.post(
            "/api/pagos/webhook",
            json={"topic": "payment", "data": {"id": 123}},
        )
        # Debe devolver 200 aunque no haya SDK (no rompe)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
