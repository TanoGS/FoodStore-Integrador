"""
test_pedido_crud.py — Tests de integración del CRUD de Pedidos.
================================================================
Endpoints cubiertos:
- POST /api/pedidos/              → crear pedido
- GET  /api/pedidos/              → listar pedidos propios
- GET  /api/pedidos/{id}          → detalle de pedido

Reglas de negocio probadas:
- EN_LOCAL + EFECTIVO → 201 creado
- DELIVERY sin dirección → 422
- DELIVERY con EFECTIVO → 422
- Cliente solo ve sus pedidos
"""
import pytest


@pytest.mark.integration
class TestPedidoCrear:
    """Tests de creación de pedidos."""

    def test_crear_pedido_en_local_efectivo_devuelve_201(
        self, client, test_user, test_producto, db_session
    ):
        """EN_LOCAL + EFECTIVO debe crear el pedido sin dirección."""
        from tests.conftest import auth_headers

        headers = auth_headers(test_user, db_session)
        response = client.post(
            "/api/pedidos/",
            headers=headers,
            json={
                "tipo_entrega": "EN_LOCAL",
                "forma_pago_codigo": "EFECTIVO",
                "detalles": [{"producto_id": test_producto.id, "cantidad": 2}],
            },
        )
        assert response.status_code == 201, f"Error: {response.json()}"
        data = response.json()
        assert data["estado_codigo"] == "PENDIENTE"
        assert data["forma_pago_codigo"] == "EFECTIVO"
        assert data["tipo_entrega"] == "EN_LOCAL"

    def test_crear_pedido_delivery_requiere_direccion_y_mp(
        self, client, test_user, test_producto, db_session
    ):
        """DELIVERY sin direccion_id debe devolver 422."""
        from tests.conftest import auth_headers

        headers = auth_headers(test_user, db_session)
        response = client.post(
            "/api/pedidos/",
            headers=headers,
            json={
                "tipo_entrega": "DELIVERY",
                "direccion_id": None,
                "forma_pago_codigo": "MERCADOPAGO",
                "detalles": [{"producto_id": test_producto.id, "cantidad": 1}],
            },
        )
        assert response.status_code == 422

    def test_crear_pedido_delivery_con_efectivo_rechazado(
        self, client, test_user, test_producto, db_session
    ):
        """DELIVERY con EFECTIVO debe ser rechazado (solo MP para delivery)."""
        from tests.conftest import auth_headers

        headers = auth_headers(test_user, db_session)
        response = client.post(
            "/api/pedidos/",
            headers=headers,
            json={
                "tipo_entrega": "DELIVERY",
                "direccion_id": 1,  # existe pero no debería importar
                "forma_pago_codigo": "EFECTIVO",
                "detalles": [{"producto_id": test_producto.id, "cantidad": 1}],
            },
        )
        assert response.status_code == 422

    def test_crear_pedido_delivery_con_mp_y_direccion(
        self, client, test_user, test_producto, test_direccion, db_session
    ):
        """DELIVERY + MERCADOPAGO + direccion debe crear el pedido."""
        from tests.conftest import auth_headers

        headers = auth_headers(test_user, db_session)
        response = client.post(
            "/api/pedidos/",
            headers=headers,
            json={
                "tipo_entrega": "DELIVERY",
                "direccion_id": test_direccion.id,
                "forma_pago_codigo": "MERCADOPAGO",
                "detalles": [{"producto_id": test_producto.id, "cantidad": 1}],
            },
        )
        assert response.status_code == 201, f"Error: {response.json()}"
        data = response.json()
        assert data["estado_codigo"] == "PENDIENTE"


@pytest.mark.integration
class TestPedidoListar:
    """Tests de listado de pedidos."""

    def test_listar_pedidos_cliente_solo_ve_los_propios(
        self, client, test_user, test_producto, db_session
    ):
        """GET /pedidos/ debe devolver solo los pedidos del usuario autenticado."""
        from tests.conftest import auth_headers

        headers = auth_headers(test_user, db_session)

        # Crear un pedido primero
        client.post(
            "/api/pedidos/",
            headers=headers,
            json={
                "tipo_entrega": "EN_LOCAL",
                "forma_pago_codigo": "EFECTIVO",
                "detalles": [{"producto_id": test_producto.id, "cantidad": 1}],
            },
        )

        # Listar pedidos
        response = client.get("/api/pedidos/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "pedidos" in data
        # Todos los pedidos deben ser del usuario autenticado
        for pedido in data["pedidos"]:
            assert pedido["usuario_id"] == test_user.id

    def test_listar_pedidos_sin_auth_devuelve_401(self, client):
        """GET /pedidos/ sin JWT debe devolver 401."""
        response = client.get("/api/pedidos/")
        assert response.status_code == 401
