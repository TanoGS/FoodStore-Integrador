"""
test_pedido_schemas.py — Tests de validación de schemas Pydantic.
================================================================
Unit tests que verifican las reglas de negocio en los schemas sin HTTP ni BD.

Reglas validadas:
- PedidoCreate: DELIVERY requiere direccion_id + MERCADOPAGO
- PedidoCreate: EN_LOCAL no requiere dirección
- AvanzarEstadoRequest: CANCELADO requiere motivo
"""
import pytest
from pydantic import ValidationError
from app.modules.pedido.models import TipoEntrega, FormaPago, EstadoPedido
from app.modules.pedido.schemas import PedidoCreate, ItemPedidoCreate, AvanzarEstadoRequest


@pytest.mark.unit
class TestPedidoCreateSchema:
    """Tests de validación para PedidoCreate."""

    def test_delivery_sin_direccion_es_rechazado(self):
        """DELIVERY sin direccion_id debe fallar con ValueError."""
        with pytest.raises(ValueError, match="dirección.*obligatoria"):
            PedidoCreate(
                tipo_entrega=TipoEntrega.DELIVERY,
                direccion_id=None,
                forma_pago_codigo="MERCADOPAGO",
                detalles=[ItemPedidoCreate(producto_id=1, cantidad=1)],
            )

    def test_delivery_con_efectivo_es_rechazado(self):
        """DELIVERY con EFECTIVO debe fallar (solo MP)."""
        with pytest.raises(ValueError, match="MercadoPago"):
            PedidoCreate(
                tipo_entrega=TipoEntrega.DELIVERY,
                direccion_id=1,
                forma_pago_codigo="EFECTIVO",
                detalles=[ItemPedidoCreate(producto_id=1, cantidad=1)],
            )

    def test_delivery_con_mp_y_direccion_pasa(self):
        """DELIVERY con MERCADOPAGO y direccion_id debe pasar."""
        pedido = PedidoCreate(
            tipo_entrega=TipoEntrega.DELIVERY,
            direccion_id=1,
            forma_pago_codigo="MERCADOPAGO",
            detalles=[ItemPedidoCreate(producto_id=1, cantidad=1)],
        )
        assert pedido.tipo_entrega == TipoEntrega.DELIVERY
        assert pedido.direccion_id == 1

    def test_en_local_no_requiere_direccion(self):
        """EN_LOCAL no requiere direccion_id (puede pasar None)."""
        pedido = PedidoCreate(
            tipo_entrega=TipoEntrega.EN_LOCAL,
            direccion_id=None,
            forma_pago_codigo="EFECTIVO",
            detalles=[ItemPedidoCreate(producto_id=1, cantidad=1)],
        )
        assert pedido.tipo_entrega == TipoEntrega.EN_LOCAL

    def test_en_local_puede_usar_efectivo(self):
        """EN_LOCAL con EFECTIVO debe pasar."""
        pedido = PedidoCreate(
            tipo_entrega=TipoEntrega.EN_LOCAL,
            direccion_id=None,
            forma_pago_codigo="EFECTIVO",
            detalles=[ItemPedidoCreate(producto_id=1, cantidad=1)],
        )
        assert pedido.forma_pago_codigo == "EFECTIVO"

    def test_en_local_puede_usar_mercadopago(self):
        """EN_LOCAL con MERCADOPAGO debe pasar (pago antecipado online)."""
        pedido = PedidoCreate(
            tipo_entrega=TipoEntrega.EN_LOCAL,
            direccion_id=None,
            forma_pago_codigo="MERCADOPAGO",
            detalles=[ItemPedidoCreate(producto_id=1, cantidad=1)],
        )
        assert pedido.forma_pago_codigo == "MERCADOPAGO"

    def test_detalles_vacios_es_rechazado(self):
        """Pedido sin detalles debe fallar (min_length=1 implícito)."""
        with pytest.raises(ValidationError):
            PedidoCreate(
                tipo_entrega=TipoEntrega.EN_LOCAL,
                direccion_id=None,
                forma_pago_codigo="EFECTIVO",
                detalles=[],
            )


@pytest.mark.unit
class TestAvanzarEstadoSchema:
    """Tests de validación para AvanzarEstadoRequest."""

    def test_cancelar_sin_motivo_es_rechazado(self):
        """Cancelar pedido sin motivo debe fallar."""
        with pytest.raises(ValueError, match="motivo.*obligatorio"):
            AvanzarEstadoRequest(
                estado_hacia=EstadoPedido.CANCELADO,
                motivo=None,
            )

    def test_cancelar_con_motivo_pasa(self):
        """Cancelar pedido con motivo debe pasar."""
        req = AvanzarEstadoRequest(
            estado_hacia=EstadoPedido.CANCELADO,
            motivo="Cliente solicitó cancelación",
        )
        assert req.motivo == "Cliente solicitó cancelación"

    def test_avanzar_sin_motivo_es_valido(self):
        """Avanzar a cualquier estado que no sea CANCELADO no requiere motivo."""
        for estado in [EstadoPedido.CONFIRMADO, EstadoPedido.EN_PREPARACION, EstadoPedido.EN_CAMINO]:
            req = AvanzarEstadoRequest(estado_hacia=estado, motivo=None)
            assert req.estado_hacia == estado
