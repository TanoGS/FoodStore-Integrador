"""
tests/integration/test_rate_limit.py
======================================

Pruebas de integración del RateLimitMiddleware.

Verificamos:
  - El rate limit devuelve 429 cuando se excede.
  - Los headers X-RateLimit-* están presentes.
  - El rate limit en endpoints de auth es más estricto.

NOTA: el conftest resetea los limiters antes de cada test, así que
cada test parte de un estado limpio.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit.rate_limit_middleware import RateLimitMiddleware


# ===========================================================================
# TESTS: Rate limit general
# ===========================================================================
class TestRateLimitDefault:
    """Tests del limiter por defecto (endpoints no auth)."""

    def test_response_includes_ratelimit_headers(self, client: TestClient):
        """
        Toda response de un endpoint rate-limiteado trae headers
        X-RateLimit-*. Usamos /productos/ que NO está excluido.
        """
        response = client.get("/productos/")
        assert "x-ratelimit-limit" in response.headers
        assert "x-ratelimit-remaining" in response.headers

    def test_429_when_burst_exhausted(self, client: TestClient):
        """
        Agotar la ráfaga inicial → 429 con código rate_limit_exceeded.
        Usamos /productos/ porque / está excluido del rate limit.
        """
        statuses = []
        for _ in range(80):
            r = client.get("/productos/")
            statuses.append(r.status_code)

        # Al menos UN request debe haber sido bloqueado.
        assert 429 in statuses

    def test_429_includes_retry_after(self, client: TestClient):
        """
        Cuando se devuelve 429, el header `Retry-After` indica
        cuántos segundos esperar.
        """
        # Agotamos el bucket.
        for _ in range(80):
            client.get("/productos/")
        # El próximo request es 429.
        r = client.get("/productos/")
        assert r.status_code == 429
        assert "retry-after" in r.headers
        # El valor es un entero (segundos).
        retry_after = int(r.headers["retry-after"])
        assert retry_after > 0


# ===========================================================================
# TESTS: Rate limit en endpoints de auth
# ===========================================================================
class TestRateLimitAuth:
    """
    El limiter de auth es MÁS ESTRICTO que el general. Verificamos que
    se aplica a /usuarios/token y /usuarios/register.
    """

    def test_auth_endpoint_has_stricter_limit(self, client: TestClient):
        """
        Un endpoint de auth se rate-limita ANTES que uno general.
        Como el auth_limiter tiene capacity menor, se bloquea primero.
        """
        # Spameamos el endpoint de login con credenciales inválidas.
        statuses = []
        for _ in range(30):
            r = client.post(
                "/usuarios/token",
                data={"username": "nobody", "password": "wrong"},
            )
            statuses.append(r.status_code)

        # Esperamos ver algún 429 antes que el rate limit general
        # (capacity 60) se agote.
        assert 429 in statuses
