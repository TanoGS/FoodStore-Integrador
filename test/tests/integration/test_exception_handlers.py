"""
tests/integration/test_exception_handlers.py
=============================================

Pruebas de los exception handlers globales.

Verificamos que TODOS los errores de la API se devuelvan con el formato
JSON unificado:
    {
        "error": {
            "code": "...",
            "message": "...",
            "request_id": "...",
            "timestamp": "..."
        }
    }
"""

import pytest
from fastapi.testclient import TestClient


# ===========================================================================
# TESTS: Formato unificado
# ===========================================================================
class TestUnifiedErrorFormat:
    """El response de TODA excepción tiene la misma forma JSON."""

    def test_404_has_unified_format(self, client: TestClient):
        """
        Un GET a un endpoint inexistente devuelve 404 con nuestro
        formato (no el default de FastAPI).
        """
        response = client.get("/this-path-does-not-exist")
        assert response.status_code == 404
        data = response.json()
        # El formato tiene la clave "error" envolviendo todo.
        assert "error" in data
        err = data["error"]
        assert "code" in err
        assert "message" in err
        assert "request_id" in err
        assert "timestamp" in err

    def test_422_validation_error_format(self, client: TestClient):
        """
        Body inválido (ej: tipos incorrectos) → 422 con formato.
        Pydantic detecta el error y nuestro handler lo formatea.
        """
        # `register` espera username (str), email (str), password (str).
        # Mandamos un int en vez de str.
        response = client.post(
            "/usuarios/register",
            json={"username": 123, "email": "x@x.com", "password": "12345678"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        err = data["error"]
        # El código identifica el tipo de error.
        assert err["code"] in ("validation_error", "unprocessable_entity")

    def test_401_unauthenticated(self, client: TestClient):
        """
        Un endpoint protegido sin token → 401 con formato unificado.
        """
        # /usuarios/me requiere auth.
        response = client.get("/usuarios/me")
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert "code" in data["error"]

    def test_403_forbidden(self, client: TestClient, user_auth_headers: dict):
        """
        Un user normal intentando acceder a un endpoint de admin
        → 403 con formato unificado.
        """
        # /usuarios/ (lista) requiere rol admin.
        response = client.get("/usuarios/", headers=user_auth_headers)
        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert "code" in data["error"]


# ===========================================================================
# TESTS: Excepciones de dominio (AppError)
# ===========================================================================
class TestDomainExceptions:
    """
    Excepciones definidas en `app/core/exceptions/custom_exceptions.py`
    (DuplicateResourceError, ResourceNotFoundError, etc.).
    """

    def test_duplicate_username_returns_409(self, client: TestClient, admin_auth_headers: dict):
        """
        Registrar un username duplicado → 409 Conflict.
        """
        # /register es público (no necesita headers). Solo creamos UNA vez.
        payload = {
            "username": "duplicate_test",
            "email": "dup1@example.com",
            "password": "TestPass123!",
        }
        r1 = client.post("/usuarios/register", json=payload)
        assert r1.status_code == 201, f"Setup falló: {r1.json()}"

        # El segundo con mismo username (distinto email) debe fallar.
        payload2 = {**payload, "email": "dup2@example.com"}
        r2 = client.post("/usuarios/register", json=payload2)
        assert r2.status_code == 409
        data = r2.json()
        assert "error" in data
        assert data["error"]["code"] == "duplicate_resource"

    def test_not_found_returns_404(self, client: TestClient, admin_auth_headers: dict):
        """
        GET /usuarios/{id} con id inexistente → 404.
        """
        response = client.get("/usuarios/999999", headers=admin_auth_headers)
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "not_found"

    def test_invalid_login_returns_401(self, client: TestClient):
        """
        Login con password incorrecto → 401 con mensaje genérico.
        """
        response = client.post(
            "/usuarios/token",
            data={"username": "admin", "password": "wrong_password"},
        )
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        # El código identifica el tipo (no leakeamos "user not found"
        # vs "wrong password" para no dar pistas al atacante).
        assert data["error"]["code"] in ("authentication_error", "unauthorized")
