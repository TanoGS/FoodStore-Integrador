"""
test_pedido_fsm.py — Tests de la Máquina de Estados Finita de Pedidos.
=======================================================================
Unit tests que verifican la lógica pura de FSM sin HTTP ni BD.

FSM mapa (desde app.modules.pedido.service):
    PENDIENTE      → CONFIRMADO, CANCELADO
    CONFIRMADO     → EN_PREPARACION, CANCELADO
    EN_PREPARACION → EN_CAMINO, CANCELADO
    EN_CAMINO      → ENTREGADO
    ENTREGADO      → [] (terminal)
    CANCELADO      → [] (terminal)
"""
import pytest
from app.modules.pedido.models import EstadoPedido
from app.modules.pedido.service import _FSM


@pytest.mark.unit
class TestPedidoFSM:
    """Suite de tests para la FSM de pedidos."""

    def test_fsm_pendiente_permite_confirmar_y_cancelar(self):
        """PENDIENTE puede avanzar a CONFIRMADO o CANCELADO."""
        assert EstadoPedido.CONFIRMADO in _FSM[EstadoPedido.PENDIENTE]
        assert EstadoPedido.CANCELADO in _FSM[EstadoPedido.PENDIENTE]

    def test_fsm_confirmado_permite_preparacion_y_cancelar(self):
        """CONFIRMADO puede avanzar a EN_PREPARACION o CANCELADO."""
        assert EstadoPedido.EN_PREPARACION in _FSM[EstadoPedido.CONFIRMADO]
        assert EstadoPedido.CANCELADO in _FSM[EstadoPedido.CONFIRMADO]

    def test_fsm_en_preparacion_permite_camino_y_cancelar(self):
        """EN_PREPARACION puede avanzar a EN_CAMINO o CANCELADO."""
        assert EstadoPedido.EN_CAMINO in _FSM[EstadoPedido.EN_PREPARACION]
        assert EstadoPedido.CANCELADO in _FSM[EstadoPedido.EN_PREPARACION]

    def test_fsm_en_camino_solo_permite_entregado(self):
        """EN_CAMINO solo puede avanzar a ENTREGADO."""
        assert _FSM[EstadoPedido.EN_CAMINO] == [EstadoPedido.ENTREGADO]

    def test_fsm_entregado_y_cancelado_son_terminales(self):
        """ENTREGADO y CANCELADO son estados terminales (sin transiciones)."""
        assert _FSM[EstadoPedido.ENTREGADO] == []
        assert _FSM[EstadoPedido.CANCELADO] == []

    def test_fsm_rechaza_salto_de_estado_invalido(self):
        """CONFIRMADO no puede ir directo a ENTREGADO (debe pasar por EN_CAMINO)."""
        assert EstadoPedido.ENTREGADO not in _FSM[EstadoPedido.CONFIRMADO]

    def test_fsm_rechaza_pedido_cancelado_a_cualquier_estado(self):
        """CANCELADO no puede avanzar a ningún estado."""
        for estado in EstadoPedido:
            if estado != EstadoPedido.CANCELADO:
                assert estado not in _FSM[EstadoPedido.CANCELADO]

    def test_fsm_todos_los_estados_tienen_definicion(self):
        """Todos los valores del enum EstadoPedido tienen entrada en el mapa FSM."""
        for estado in EstadoPedido:
            assert estado in _FSM, f"Falta definición FSM para {estado}"
