"""
tests/integration/test_productos.py
====================================

Pruebas de integración del CRUD de Productos. Cubre:
  - POST: happy path, validaciones, duplicados.
  - GET: lista vacía, lista con datos, filtros, get by id, 404.
  - PATCH: actualización parcial, 404, validaciones.
  - DELETE: soft delete, RBAC.
"""

import pytest
from fastapi.testclient import TestClient


# ===========================================================================
# TESTS: POST /productos/
# ===========================================================================
class TestCreateProducto:
    """POST /productos/"""

    def test_create_returns_201_with_full_schema(
        self, client: TestClient, admin_auth_headers: dict, producto_payload: dict
    ):
        """Happy path: 201 con el schema completo (incluye id)."""
        response = client.post("/productos/", json=producto_payload, headers=admin_auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["nombre"] == producto_payload["nombre"]
        assert data["precio"] == producto_payload["precio"]
        assert data["stock"] == producto_payload["stock"]

    def test_create_without_auth_returns_401(self, client: TestClient, producto_payload: dict):
        """Sin auth → 401."""
        response = client.post("/productos/", json=producto_payload)
        assert response.status_code == 401

    @pytest.mark.parametrize("payload,id", [
        pytest.param({"precio": 50.0, "stock": 5}, "sin-nombre", id="sin-nombre"),
        pytest.param({"nombre": "X", "stock": 5}, "sin-precio", id="sin-precio"),
        pytest.param({"nombre": "X", "precio": -1.0, "stock": 5}, "precio-negativo", id="precio-negativo"),
        pytest.param({"nombre": "X", "precio": 10, "stock": -1}, "stock-negativo", id="stock-negativo"),
        pytest.param({"nombre": "", "precio": 10, "stock": 0}, "nombre-vacio", id="nombre-vacio"),
    ])
    def test_create_invalid_input_returns_422(
        self, client: TestClient, admin_auth_headers: dict, payload: dict, id: str
    ):
        """Datos inválidos → 422."""
        response = client.post("/productos/", json=payload, headers=admin_auth_headers)
        assert response.status_code == 422

    def test_create_duplicate_name_returns_409(
        self, client: TestClient, admin_auth_headers: dict, created_producto: dict
    ):
        """Nombre duplicado → 409."""
        payload = {
            "nombre": created_producto["nombre"],
            "precio": 99.99,
            "stock": 5,
        }
        response = client.post("/productos/", json=payload, headers=admin_auth_headers)
        assert response.status_code == 409


# ===========================================================================
# TESTS: GET /productos/
# ===========================================================================
class TestListProductos:
    """GET /productos/ (búsqueda paginada)"""

    def test_list_empty(self, client: TestClient):
        """Sin productos → lista vacía con total=0."""
        response = client.get("/productos/")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_contains_created(
        self, client: TestClient, created_producto: dict
    ):
        """Después de crear, el producto aparece en la lista."""
        response = client.get("/productos/")
        assert response.status_code == 200
        ids = [p["id"] for p in response.json()["items"]]
        assert created_producto["id"] in ids

    def test_filter_by_categoria(
        self, client: TestClient, admin_auth_headers: dict
    ):
        """Filtrar por categoría devuelve solo los que matchean."""
        # Creamos dos productos de categorías distintas.
        client.post(
            "/productos/",
            json={"nombre": "ProdTecno1", "precio": 100, "categoria": "tecnologia"},
            headers=admin_auth_headers,
        )
        client.post(
            "/productos/",
            json={"nombre": "ProdHogar1", "precio": 50, "categoria": "hogar"},
            headers=admin_auth_headers,
        )

        # Filtramos por tecnologia.
        response = client.get("/productos/?categoria=tecnologia")
        assert response.status_code == 200
        items = response.json()["items"]
        assert all(p["categoria"] == "tecnologia" for p in items)
        assert len(items) >= 1

    def test_filter_by_price_range(
        self, client: TestClient, admin_auth_headers: dict
    ):
        """Filtro por rango de precio."""
        client.post(
            "/productos/",
            json={"nombre": "Barato", "precio": 5, "categoria": "test"},
            headers=admin_auth_headers,
        )
        client.post(
            "/productos/",
            json={"nombre": "Caro", "precio": 999, "categoria": "test"},
            headers=admin_auth_headers,
        )

        response = client.get("/productos/?min_precio=10&max_precio=100")
        assert response.status_code == 200
        items = response.json()["items"]
        for p in items:
            assert 10 <= p["precio"] <= 100


# ===========================================================================
# TESTS: GET /productos/{id}
# ===========================================================================
class TestGetProducto:
    """GET /productos/{id}"""

    def test_get_by_id_returns_correct_data(
        self, client: TestClient, created_producto: dict
    ):
        pid = created_producto["id"]
        response = client.get(f"/productos/{pid}")
        assert response.status_code == 200
        assert response.json()["nombre"] == created_producto["nombre"]

    def test_get_nonexistent_returns_404(self, client: TestClient):
        response = client.get("/productos/999999")
        assert response.status_code == 404

    def test_get_invalid_id_type_returns_422(self, client: TestClient):
        """ID no numérico → 422 (validación de tipo de Pydantic)."""
        response = client.get("/productos/not-a-number")
        assert response.status_code == 422


# ===========================================================================
# TESTS: PATCH /productos/{id}
# ===========================================================================
class TestUpdateProducto:
    """PATCH /productos/{id}"""

    def test_update_single_field_leaves_others_unchanged(
        self, client: TestClient, admin_auth_headers: dict, created_producto: dict
    ):
        pid = created_producto["id"]
        response = client.patch(
            f"/productos/{pid}",
            json={"precio": 199.99},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["precio"] == 199.99
        # Otros campos sin cambios.
        assert data["nombre"] == created_producto["nombre"]
        assert data["stock"] == created_producto["stock"]

    def test_update_nonexistent_returns_404(self, client: TestClient, admin_auth_headers: dict):
        response = client.patch(
            "/productos/999999",
            json={"precio": 50.0},
            headers=admin_auth_headers,
        )
        assert response.status_code == 404

    def test_update_invalid_price_returns_422(
        self, client: TestClient, admin_auth_headers: dict, created_producto: dict
    ):
        pid = created_producto["id"]
        response = client.patch(
            f"/productos/{pid}",
            json={"precio": -10.0},
            headers=admin_auth_headers,
        )
        assert response.status_code == 422


# ===========================================================================
# TESTS: DELETE (soft) /productos/admin/{id}/descontinuar
# ===========================================================================
class TestDeleteProducto:
    """Soft delete de productos."""

    def test_normal_user_cannot_descontinuar(
        self, client: TestClient, user_auth_headers: dict, created_producto: dict
    ):
        """User normal NO puede descontinuar (es acción de admin)."""
        pid = created_producto["id"]
        response = client.post(
            f"/productos/admin/{pid}/descontinuar",
            headers=user_auth_headers,
        )
        assert response.status_code == 403

    def test_admin_can_descontinuar(
        self, client: TestClient, admin_auth_headers: dict, created_producto: dict
    ):
        """Admin SÍ puede descontinuar."""
        pid = created_producto["id"]
        response = client.post(
            f"/productos/admin/{pid}/descontinuar",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_get_after_descontinuar_returns_404(
        self, client: TestClient, admin_auth_headers: dict, created_producto: dict
    ):
        """GET después de descontinuar → 404 (no aparece en listados activos)."""
        pid = created_producto["id"]
        client.post(
            f"/productos/admin/{pid}/descontinuar",
            headers=admin_auth_headers,
        )
        response = client.get(f"/productos/{pid}")
        assert response.status_code == 404
