"""
tests/integration/test_middlewares.py
======================================

Pruebas de integración para los middlewares (Logging, Timing).

Patrón (cap12):
---------------
- Usamos TestClient (FastAPI) con dependency_overrides.
- Cada test verifica el comportamiento de un middleware específico.
- Tests parametrizados con `pytest.param(..., id="...")` para
  documentar casos.
"""

import time

import pytest
from fastapi.testclient import TestClient


# ===========================================================================
# TESTS: Logging Middleware
# ===========================================================================
class TestLoggingMiddleware:
    """
    El LoggingMiddleware agrega un `X-Request-ID` y loguea cada request.
    Verificamos que el header esté presente y que tenga formato UUID.
    """

    def test_request_id_header_present(self, client: TestClient):
        """El response incluye el header `X-Request-ID`."""
        # Usamos /productos/ porque / está excluido de middlewares
        # (es un health check). Pero como requiere auth, usamos /.
        response = client.get("/")
        assert response.status_code == 200
        assert "x-request-id" in response.headers

    def test_request_id_is_uuid_format(self, client: TestClient):
        """
        El request_id es un UUID válido (4 segmentos hexadecimales).
        Si no fuera UUID, indicaría un bug en el middleware.
        """
        import uuid
        response = client.get("/")
        request_id = response.headers["x-request-id"]
        # Si no es UUID, `uuid.UUID(...)` lanza ValueError.
        parsed = uuid.UUID(request_id)
        assert parsed.version == 4  # UUID v4 (random)

    def test_request_id_unique_per_request(self, client: TestClient):
        """
        Dos requests distintos deben tener request_ids distintos.
        Si no, no estamos generando IDs únicos.
        """
        r1 = client.get("/")
        r2 = client.get("/")
        assert r1.headers["x-request-id"] != r2.headers["x-request-id"]

    def test_request_id_set_on_state_for_handlers(self, client: TestClient):
        """
        El middleware guarda el request_id en `request.state` para que
        los exception handlers lo usen en sus respuestas JSON.
        Lo verificamos indirectamente: un 404 incluye el request_id en
        la respuesta.
        """
        response = client.get("/this-does-not-exist")
        assert response.status_code == 404
        body = response.json()
        assert "error" in body
        # El request_id en el body DEBE coincidir con el header.
        assert body["error"]["request_id"] == response.headers["x-request-id"]


# ===========================================================================
# TESTS: Timing Middleware
# ===========================================================================
class TestTimingMiddleware:
    """
    El TimingMiddleware mide el tiempo de procesamiento y lo expone
    en headers. Verificamos:
      - `X-Response-Time-ms`: tiempo en milisegundos.
      - `Server-Timing`: header estándar W3C.
    """

    def test_response_time_header_present(self, client: TestClient):
        """El response incluye `X-Response-Time-ms`."""
        response = client.get("/")
        assert "x-response-time-ms" in response.headers

    def test_response_time_is_numeric(self, client: TestClient):
        """El valor de X-Response-Time-ms es parseable como float."""
        response = client.get("/")
        ms = float(response.headers["x-response-time-ms"])
        assert ms >= 0

    def test_response_time_reasonable(self, client: TestClient):
        """
        El tiempo reportado es razonable (entre 0 y 5 segundos).
        Si fuera 0, no estaríamos midiendo. Si fuera 5000ms, hay un
        problema grave de performance.
        """
        response = client.get("/")
        ms = float(response.headers["x-response-time-ms"])
        assert 0 <= ms < 5000

    def test_server_timing_header_present(self, client: TestClient):
        """
        El header estándar `Server-Timing` está presente y describe
        el tiempo total (`total`).
        """
        response = client.get("/")
        assert "server-timing" in response.headers
        assert "total" in response.headers["server-timing"]
