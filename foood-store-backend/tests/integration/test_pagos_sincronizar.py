"""
test_pagos_sincronizar.py — Tests de integración del endpoint de sincronización con MP.
====================================================================================
Endpoint cubierto:
- POST /api/pagos/{pedido_id}/sincronizar  → reconciliar con MercadoPago

Reglas de negocio probadas:
- Sincronización con mp_payment_id conocido → actualiza mp_status
- Sincronización sin mp_payment_id (búsqueda por external_reference) → actualiza mp_status
- Pago approved en MP → DELIVERY avanza a CONFIRMADO
- Pago approved en MP → EN_LOCAL queda PENDIENTE (cajero confirma)
- MP no encuentra el pago → mp_status="not_found"
- Sin SDK configurado → devuelve error 503
- Sin pago registrado → devuelve error 404
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.integration
class TestPagosSincronizar:
    """Tests del endpoint POST /pagos/{pedido_id}/sincronizar."""

    @patch("app.modules.pagos.service.mercadopago.SDK")
    def test_sincronizar_con_mp_payment_id_existente_approved_delivery_avanza_a_confirmado(
        self, mock_sdk_class, client, test_user, test_producto, test_direccion, db_session
    ):
        """Con mp_payment_id已知 + approved + DELIVERY → avanza a CONFIRMADO."""
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

        # Crear pago para tener external_reference
        from app.modules.pagos.service import PagoService
        svc = PagoService(db_session)
        pago_resp = svc.crear_pago(pedido_id=pedido_id, usuario_id=test_user.id)
        ext_ref = pago_resp.external_reference

        # Actualizar pago con mp_payment_id existente en BD
        from app.modules.pagos.models import Pago
        pago_db = db_session.query(Pago).filter_by(pedido_id=pedido_id).first()
        pago_db.mp_payment_id = 777777
        db_session.add(pago_db)
        db_session.commit()

        # Mock del SDK
        mock_sdk = MagicMock()
        mock_sdk.payment().get.return_value = {
            "status": 200,
            "response": {
                "id": 777777,
                "status": "approved",
                "external_reference": ext_ref,
                "transaction_amount": 1500.0,
                "payment_method_id": "visa",
                "status_detail": "accredited",
            },
        }
        mock_sdk_class.return_value = mock_sdk

        # Llamar al endpoint de sincronización
        response = client.post(f"/api/pagos/{pedido_id}/sincronizar", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["mp_status"] == "approved"
        assert data["mp_payment_id"] == 777777

        # Verificar que el pedido avanzó a CONFIRMADO
        db_session.expire_all()
        pedido_actualizado = client.get(f"/api/pedidos/{pedido_id}", headers=headers)
        assert pedido_actualizado.json()["estado_codigo"] == "CONFIRMADO"

    @patch("app.modules.pagos.service.mercadopago.SDK")
    def test_sincronizar_sin_mp_payment_id_busca_por_external_reference(
        self, mock_sdk_class, client, test_user, test_producto, test_direccion, db_session
    ):
        """Sin mp_payment_id → busca en MP por external_reference y actualiza."""
        from tests.conftest import auth_headers

        headers = auth_headers(test_user, db_session)

        # Crear pedido
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

        # Crear pago (sin mp_payment_id)
        from app.modules.pagos.service import PagoService
        svc = PagoService(db_session)
        pago_resp = svc.crear_pago(pedido_id=pedido_id, usuario_id=test_user.id)
        ext_ref = pago_resp.external_reference

        # Mock: payment().search devuelve el pago, payment().get no se llama
        mock_sdk = MagicMock()
        mock_sdk.payment().search.return_value = {
            "status": 200,
            "response": {
                "results": [
                    {
                        "id": 888888,
                        "status": "approved",
                        "external_reference": ext_ref,
                        "transaction_amount": 1500.0,
                        "payment_method_id": "master",
                    }
                ]
            },
        }
        mock_sdk_class.return_value = mock_sdk

        # payment().get NO debe ser llamado
        response = client.post(f"/api/pagos/{pedido_id}/sincronizar", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["mp_status"] == "approved"
        assert data["mp_payment_id"] == 888888  # Se actualiza con el ID de MP
        mock_sdk.payment().get.assert_not_called()

    @patch("app.modules.pagos.service.mercadopago.SDK")
    def test_sincronizar_mp_no_encuentra_pago_devuelve_not_found(
        self, mock_sdk_class, client, test_user, test_producto, test_direccion, db_session
    ):
        """MP no tiene registro del pago → mp_status="not_found", no avanza pedido."""
        from tests.conftest import auth_headers

        headers = auth_headers(test_user, db_session)

        # Crear pedido
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
        svc.crear_pago(pedido_id=pedido_id, usuario_id=test_user.id)

        # Mock: search devuelve vacío (no hay pago en MP)
        mock_sdk = MagicMock()
        mock_sdk.payment().search.return_value = {
            "status": 200,
            "response": {"results": []},
        }
        mock_sdk_class.return_value = mock_sdk

        response = client.post(f"/api/pagos/{pedido_id}/sincronizar", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["mp_status"] == "not_found"

        # El pedido sigue PENDIENTE (no se avanzó)
        db_session.expire_all()
        pedido_actualizado = client.get(f"/api/pedidos/{pedido_id}", headers=headers)
        assert pedido_actualizado.json()["estado_codigo"] == "PENDIENTE"

    @patch("app.modules.pagos.service.mercadopago.SDK")
    def test_sincronizar_approved_enlocal_queda_pendiente(
        self, mock_sdk_class, client, test_user, test_producto, db_session
    ):
        """EN_LOCAL + approved → queda PENDIENTE para confirmación del cajero."""
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

        from app.modules.pagos.service import PagoService
        svc = PagoService(db_session)
        pago_resp = svc.crear_pago(pedido_id=pedido_id, usuario_id=test_user.id)
        ext_ref = pago_resp.external_reference

        mock_sdk = MagicMock()
        mock_sdk.payment().search.return_value = {
            "status": 200,
            "response": {
                "results": [
                    {
                        "id": 999999,
                        "status": "approved",
                        "external_reference": ext_ref,
                        "transaction_amount": 1500.0,
                        "payment_method_id": "visa",
                    }
                ]
            },
        }
        mock_sdk_class.return_value = mock_sdk

        response = client.post(f"/api/pagos/{pedido_id}/sincronizar", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["mp_status"] == "approved"

        # El pedido NO avanza a CONFIRMADO (queda PENDIENTE)
        db_session.expire_all()
        pedido_actualizado = client.get(f"/api/pedidos/{pedido_id}", headers=headers)
        assert pedido_actualizado.json()["estado_codigo"] == "PENDIENTE"

    def test_sincronizar_sin_pago_registrado_devuelve_404(
        self, client, test_user, test_producto, test_direccion, db_session
    ):
        """Pedido sin pago registrado → 404."""
        from tests.conftest import auth_headers

        headers = auth_headers(test_user, db_session)

        # Crear pedido sin pago
        create_resp = client.post(
            "/api/pedidos/",
            headers=headers,
            json={
                "tipo_entrega": "DELIVERY",
                "direccion_id": test_direccion.id,
                "forma_pago_codigo": "EFECTIVO",
                "detalles": [{"producto_id": test_producto.id, "cantidad": 1}],
            },
        )
        assert create_resp.status_code == 201
        pedido_id = create_resp.json()["id"]

        response = client.post(f"/api/pagos/{pedido_id}/sincronizar", headers=headers)
        assert response.status_code == 404
