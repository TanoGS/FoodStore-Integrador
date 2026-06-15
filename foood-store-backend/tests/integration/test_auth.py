"""
test_auth.py — Tests de integración del módulo Auth.
================================================================
Endpoints cubiertos:
- POST /api/registro    → crear usuario
- POST /api/login       → login + JWT
- GET  /api/me          → perfil propio

Fixtures usados: client, db_session
"""
import pytest


@pytest.mark.integration
class TestAuthRegistro:
    """Tests de registro de usuarios."""

    def test_register_crea_usuario_con_password_hasheada(self, client, db_session):
        """Registro exitoso crea un usuario en la BD."""
        response = client.post(
            "/api/registro",
            json={
                "email": "nuevo@test.com",
                "password": "password123",
                "nombre": "Nuevo",
                "apellido": "Usuario",
                "cel": "3333333333",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "nuevo@test.com"
        assert "password" not in data  # password no debe exponerse
        assert data["id"] is not None

    def test_register_rechaza_email_duplicado(self, client, test_user):
        """Registrar con email ya existente devuelve 400."""
        response = client.post(
            "/api/registro",
            json={
                "email": "test_cliente@foodstore.test",  # mismo email que test_user
                "password": "password123",
                "nombre": "Duplicado",
                "apellido": "Test",
                "cel": "4444444444",
            },
        )
        assert response.status_code == 400
        assert "ya está registrado" in response.json()["detail"]

    def test_register_rechaza_cel_invalido(self, client):
        """Cel con formato inválido debe fallar."""
        response = client.post(
            "/api/registro",
            json={
                "email": "cel@test.com",
                "password": "password123",
                "nombre": "Test",
                "apellido": "User",
                "cel": "123",  # menos de 10 dígitos
            },
        )
        assert response.status_code == 422  # ValidationError de Pydantic


@pytest.mark.integration
class TestAuthLogin:
    """Tests de login y JWT."""

    def test_login_devuelve_jwt_con_credenciales_validas(self, client, test_user):
        """Login con credenciales válidas devuelve access_token y token_type."""
        response = client.post(
            "/api/login",
            data={
                "username": "test_cliente@foodstore.test",
                "password": "cliente123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_rechaza_password_invalida_con_401(self, client, test_user):
        """Login con password incorrecta devuelve 401."""
        response = client.post(
            "/api/login",
            data={
                "username": "test_cliente@foodstore.test",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
        assert "Credenciales incorrectas" in response.json()["detail"]

    def test_login_rechaza_usuario_inexistente(self, client):
        """Login con email inexistente devuelve 401."""
        response = client.post(
            "/api/login",
            data={
                "username": "noexiste@test.com",
                "password": "password123",
            },
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestAuthMe:
    """Tests del endpoint /me (perfil propio)."""

    def test_me_devuelve_perfil_con_jwt_valido(self, client, test_user, db_session):
        """GET /me con JWT válido devuelve los datos del usuario."""
        from tests.conftest import auth_headers

        headers = auth_headers(test_user, db_session)
        response = client.get("/api/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test_cliente@foodstore.test"
        assert data["nombre"] == "Cliente"

    def test_me_rechaza_sin_token_con_401(self, client):
        """GET /me sin Authorization header devuelve 401."""
        response = client.get("/api/me")
        assert response.status_code == 401
