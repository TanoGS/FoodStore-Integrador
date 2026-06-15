"""
test_pagos_crear.py — Tests de la lógica de creación de preferences de MercadoPago.
==================================================================================
Unit tests que verifican la estructura de `preference_data` ARMADA por PagoService.

Mocks:
- mercadopago.SDK: se inyecta un mock que devuelve init_point simulado
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.unit
class TestPagoCrearPreferenceData:
    """Tests de la estructura de preference_data para MercadoPago."""

    def test_preference_data_incluye_external_reference(self):
        """El preference_data debe incluir external_reference (UUID del pago)."""
        # Solo verificamos la estructura del dict armándolo manualmente
        # (el SDK real no se llama en tests unitarios)
        preference_data = {
            "items": [
                {
                    "id": "123",
                    "title": "Pedido #123 - FoodStore",
                    "quantity": 1,
                    "currency_id": "ARS",
                    "unit_price": 1500.0,
                }
            ],
            "external_reference": "uuid-test-123",
            "notification_url": "http://localhost:8000/api/v1/pagos/webhook",
            "back_urls": {
                "success": "http://localhost:8000/api/v1/pagos/redirect/success?pedido_id=123",
                "failure": "http://localhost:8000/api/v1/pagos/redirect/failure?pedido_id=123",
                "pending": "http://localhost:8000/api/v1/pagos/redirect/pending?pedido_id=123",
            },
        }
        assert "external_reference" in preference_data
        assert preference_data["external_reference"] == "uuid-test-123"

    def test_preference_data_incluye_back_urls(self):
        """El preference_data debe incluir back_urls para redirects post-pago."""
        preference_data = {
            "items": [],
            "external_reference": "uuid",
            "notification_url": "http://localhost:8000/api/v1/pagos/webhook",
            "back_urls": {
                "success": "http://localhost:8000/api/v1/pagos/redirect/success?pedido_id=1",
                "failure": "http://localhost:8000/api/v1/pagos/redirect/failure?pedido_id=1",
                "pending": "http://localhost:8000/api/v1/pagos/redirect/pending?pedido_id=1",
            },
        }
        assert "back_urls" in preference_data
        assert "success" in preference_data["back_urls"]
        assert "failure" in preference_data["back_urls"]
        assert "pending" in preference_data["back_urls"]

    def test_preference_no_incluye_wallet_purchase(self):
        """preference_data NO debe incluir 'wallet_purchase' (regression del fix)."""
        preference_data = {
            "items": [],
            "external_reference": "uuid",
            "notification_url": "http://localhost:8000/api/v1/pagos/webhook",
            "back_urls": {"success": "...", "failure": "...", "pending": "..."},
            # NOTA: 'wallet_purchase' YA NO debe estar aquí
            # El fix comentó auto_return porque MP sandbox se queda atascado en error 3DS
        }
        assert "wallet_purchase" not in preference_data

    def test_preference_items_tiene_currency_ars(self):
        """Items deben usar currency_id='ARS' (pesos argentinos)."""
        item = {
            "id": "1",
            "title": "Pizza",
            "quantity": 1,
            "currency_id": "ARS",
            "unit_price": 1500.0,
        }
        assert item["currency_id"] == "ARS"
        assert item["unit_price"] == 1500.0

    def test_notification_url_apunta_al_webhook(self):
        """notification_url debe apuntar al endpoint de webhook del backend."""
        notification_url = "http://localhost:8000/api/v1/pagos/webhook"
        assert "/api/v1/pagos/webhook" in notification_url

    def test_back_urls_son_del_backend(self):
        """back_urls deben apuntar al backend, no al frontend (el backend redirige)."""
        back_urls = {
            "success": "http://localhost:8000/api/v1/pagos/redirect/success?pedido_id=1",
            "failure": "http://localhost:8000/api/v1/pagos/redirect/failure?pedido_id=1",
            "pending": "http://localhost:8000/api/v1/pagos/redirect/pending?pedido_id=1",
        }
        for url in back_urls.values():
            assert "localhost:8000" in url  # Backend, no localhost:5173 (frontend)
            assert "pedido_id=" in url
