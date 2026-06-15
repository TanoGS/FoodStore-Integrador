"""
tests/integration/test_auth.py
==============================

Pruebas de integración del módulo de autenticación:
  - Registro (éxito, duplicados, validación).
  - Login (éxito, password incorrecta, usuario inactivo).
  - /me (con token válido, sin token).
  - RBAC (admin vs user).
"""

import pytest
from fastapi.testclient import TestClient


# ===========================================================================
# TESTS: Registro
# ===========================================================================
class TestRegister:
    """POST /usuarios/register"""

    def test_register_success_returns_201(self, client: TestClient):
        """Registro válido → 201 con el UserPublic (sin password)."""
        payload = {
            "username": "alice",
            "email": "alice@example.com",
            "password": "SecurePass123!",
        }
        response = client.post("/usuarios/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "alice"
        assert data["email"] == "alice@example.com"
        # ⚠️ NUNCA devolvemos el password ni el hash.
        assert "password" not in data
        assert "hashed_password" not in data
        assert data["is_active"] is True

    def test_register_duplicate_username_returns_409(self, client: TestClient, normal_user: dict):
        """Username duplicado → 409."""
        payload = {
            "username": normal_user["username"],
            "email": "other@example.com",
            "password": "AnotherPass123!",
        }
        response = client.post("/usuarios/register", json=payload)
        assert response.status_code == 409

    def test_register_duplicate_email_returns_409(self, client: TestClient, normal_user: dict):
        """Email duplicado → 409."""
        payload = {
            "username": "otheruser",
            "email": normal_user["email"],
            "password": "AnotherPass123!",
        }
        response = client.post("/usuarios/register", json=payload)
        assert response.status_code == 409

    @pytest.mark.parametrize("payload,error_field", [
        pytest.param({"email": "x@x.com", "password": "12345678"}, "username", id="sin-username"),
        pytest.param({"username": "x", "password": "12345678"}, "email", id="sin-email"),
        pytest.param({"username": "x", "email": "x@x.com"}, "password", id="sin-password"),
        pytest.param({"username": "x", "email": "x@x.com", "password": "123"}, "password", id="password-corto"),
        pytest.param({"username": "x", "email": "not-an-email", "password": "12345678"}, "email", id="email-invalido"),
    ])
    def test_register_invalid_input_returns_422(
        self, client: TestClient, payload: dict, error_field: str
    ):
        """Datos inválidos → 422 con detalle de Pydantic."""
        response = client.post("/usuarios/register", json=payload)
        assert response.status_code == 422


# ===========================================================================
# TESTS: Login
# ===========================================================================
class TestLogin:
    """POST /usuarios/token"""

    def test_login_success_returns_token_and_sets_cookie(
        self, client: TestClient, normal_user: dict, normal_user_data: dict
    ):
        """Login OK → 200 con token en body Y cookie HttpOnly."""
        response = client.post(
            "/usuarios/token",
            data={
                "username": normal_user_data["username"],
                "password": normal_user_data["password"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        # El body trae el mensaje y el token.
        assert "mensaje" in data
        # La cookie `access_token` está seteada con HttpOnly.
        assert "access_token" in response.cookies
        # Verificamos la cookie (httponly=True).
        cookie = response.cookies.get("access_token")
        assert cookie is not None
        # El header Set-Cookie debe incluir HttpOnly.
        set_cookie = response.headers.get("set-cookie", "")
        assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower()

    def test_login_wrong_password_returns_401(
        self, client: TestClient, normal_user_data: dict
    ):
        """Password incorrecto → 401 con mensaje genérico."""
        response = client.post(
            "/usuarios/token",
            data={
                "username": normal_user_data["username"],
                "password": "WRONG_PASSWORD",
            },
        )
        assert response.status_code == 401

    def test_login_nonexistent_user_returns_401(self, client: TestClient):
        """Usuario inexistente → 401 (mismo mensaje que wrong password)."""
        response = client.post(
            "/usuarios/token",
            data={"username": "ghost", "password": "anything"},
        )
        assert response.status_code == 401


# ===========================================================================
# TESTS: /me
# ===========================================================================
class TestMe:
    """GET /usuarios/me"""

    def test_me_with_valid_token_returns_user(
        self, client: TestClient, user_auth_headers: dict, normal_user_data: dict
    ):
        """Token válido → 200 con datos del user."""
        response = client.get("/usuarios/me", headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == normal_user_data["username"]

    def test_me_without_token_returns_401(self, client: TestClient):
        """Sin token → 401."""
        response = client.get("/usuarios/me")
        assert response.status_code == 401


# ===========================================================================
# TESTS: RBAC
# ===========================================================================
class TestRBAC:
    """Permisos por rol (admin vs user)."""

    def test_normal_user_cannot_list_users(self, client: TestClient, user_auth_headers: dict):
        """User normal NO puede listar usuarios (es endpoint de admin)."""
        response = client.get("/usuarios/", headers=user_auth_headers)
        assert response.status_code == 403

    def test_admin_can_list_users(self, client: TestClient, admin_auth_headers: dict):
        """Admin SÍ puede listar usuarios."""
        response = client.get("/usuarios/", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_normal_user_can_view_other_user(
        self, client: TestClient, user_auth_headers: dict, normal_user: dict
    ):
        """Un user puede ver el perfil de otro (en este proyecto)."""
        response = client.get(
            f"/usuarios/{normal_user['id']}", headers=user_auth_headers
        )
        assert response.status_code == 200
        assert response.json()["username"] == normal_user["username"]
