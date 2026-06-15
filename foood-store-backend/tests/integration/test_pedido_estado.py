"""
test_pedido_estado.py — Tests de integración de la FSM de pedidos via HTTP.
============================================================================
Endpoints cubiertos:
- PATCH /api/pedidos/{id}/estado  → avanzar/cancelar pedido

Reglas de negocio probadas:
- PENDIENTE → CONFIRMADO (transición válida)
- Cancelar sin motivo → 422
- Transición inválida → 422
"""
import pytest


@pytest.mark.integration
class TestPedidoEstado:
    """Tests de transición de estado de pedidos."""

    def test_avanzar_estado_paga_en_efectivo_pendiente_a_confirmado(
        self, client, test_user, test_producto, db_session
    ):
        """PENDIENTE → CONFIRMADO es transición válida."""
        from tests.conftest import auth_headers

        headers = auth_headers(test_user, db_session)

        # Crear pedido
        create_resp = client.post(
            "/api/pedidos/",
            headers=headers,
            json={
                "tipo_entrega": "EN_LOCAL",
                "forma_pago_codigo": "EFECTIVO",
                "detalles": [{"producto_id": test_producto.id, "cantidad": 1}],
            },
        )
        assert create_resp.status_code == 201
        pedido_id = create_resp.json()["id"]

        # Avanzar a CONFIRMADO (cajero/admin)
        from tests.conftest import admin_headers
        admin_h = admin_headers(db_session)
        response = client.patch(
            f"/api/pedidos/{pedido_id}/estado",
            headers=admin_h,
            json={"estado_hacia": "CONFIRMADO"},
        )
        assert response.status_code == 200, f"Error: {response.json()}"
        assert response.json()["estado_codigo"] == "CONFIRMADO"

    def test_cancelar_pedido_requiere_motivo(self, client, test_user, test_producto, db_session):
        """CANCELAR sin motivo debe devolver 422."""
        from tests.conftest import auth_headers

        headers = auth_headers(test_user, db_session)

        # Crear pedido
        create_resp = client.post(
            "/api/pedidos/",
            headers=headers,
            json={
                "tipo_entrega": "EN_LOCAL",
                "forma_pago_codigo": "EFECTIVO",
                "detalles": [{"producto_id": test_producto.id, "cantidad": 1}],
            },
        )
        assert create_resp.status_code == 201
        pedido_id = create_resp.json()["id"]

        # Intentar cancelar sin motivo
        response = client.patch(
            f"/api/pedidos/{pedido_id}/cancelar",
            headers=headers,
            json={"motivo": None},
        )
        assert response.status_code == 422

    def test_cancelar_pedido_con_motivo(self, client, test_user, test_producto, db_session):
        """CANCELAR con motivo debe avanzar el estado a CANCELADO."""
        from tests.conftest import auth_headers

        headers = auth_headers(test_user, db_session)

        # Crear pedido
        create_resp = client.post(
            "/api/pedidos/",
            headers=headers,
            json={
                "tipo_entrega": "EN_LOCAL",
                "forma_pago_codigo": "EFECTIVO",
                "detalles": [{"producto_id": test_producto.id, "cantidad": 1}],
            },
        )
        assert create_resp.status_code == 201
        pedido_id = create_resp.json()["id"]

        # Cancelar con motivo
        response = client.patch(
            f"/api/pedidos/{pedido_id}/cancelar",
            headers=headers,
            json={"motivo": "Cliente decidió no comprar"},
        )
        assert response.status_code == 200, f"Error: {response.json()}"
        assert response.json()["estado_codigo"] == "CANCELADO"

    def test_avanzar_estado_rechaza_transicion_invalida(
        self, client, test_user, test_producto, db_session
    ):
        """PENDIENTE → ENTREGADO directo debe ser rechazado."""
        from tests.conftest import auth_headers

        headers = auth_headers(test_user, db_session)

        # Crear pedido
        create_resp = client.post(
            "/api/pedidos/",
            headers=headers,
            json={
                "tipo_entrega": "EN_LOCAL",
                "forma_pago_codigo": "EFECTIVO",
                "detalles": [{"producto_id": test_producto.id, "cantidad": 1}],
            },
        )
        assert create_resp.status_code == 201
        pedido_id = create_resp.json()["id"]

        # Intentar ir directo a ENTREGADO (inválido)
        from tests.conftest import admin_headers
        admin_h = admin_headers(db_session)
        response = client.patch(
            f"/api/pedidos/{pedido_id}/estado",
            headers=admin_h,
            json={"estado_hacia": "ENTREGADO"},
        )
        assert response.status_code == 422
