from typing import Optional, List
from sqlmodel import Session, select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from core.repository import BaseRepository
from .models import Pedido, DetallePedido, HistorialEstadoPedido


class PedidoRepository(BaseRepository[Pedido]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Pedido)

    # ====================================================================
    # 1. GET POR ID CON RELACIONES CARGADAS
    # ====================================================================
    def get_by_id_with_details(self, pedido_id: int) -> Optional[Pedido]:
        """
        Obtiene un pedido con sus detalles y historial cargados eagerly.
        Evita N+1 queries.
        """
        statement = (
            select(Pedido)
            .where(Pedido.id == pedido_id)
            .options(
                selectinload(Pedido.detalles),
                selectinload(Pedido.historial)
            )
        )
        return self.session.exec(statement).first()

    def get_by_id_o_none(self, pedido_id: int) -> Optional[Pedido]:
        """Alias para compatibilidad hacia atrás."""
        return self.session.get(Pedido, pedido_id)

    # ====================================================================
    # 2. LISTAR PEDIDOS CON PAGINACIÓN
    # ====================================================================
    def get_all_activos(self, offset: int = 0, limit: int = 20) -> List[Pedido]:
        """
        Lista todos los pedidos activos ordenados por fecha descendente.
        Incluye detalles para mostrar en listados.
        """
        statement = (
            select(Pedido)
            .offset(offset)
            .limit(limit)
            .options(selectinload(Pedido.detalles))
            .order_by(Pedido.creado_en.desc())
        )
        return list(self.session.exec(statement).all())

    def count_activos(self) -> int:
        """Cuenta todos los pedidos activos usando COUNT en DB."""
        statement = select(func.count(Pedido.id))
        return self.session.exec(statement).one()

    # ====================================================================
    # 3. LISTAR PEDIDOS POR ESTADO
    # ====================================================================
    def get_all_activos_por_estado(
        self, estado_codigo: str, offset: int = 0, limit: int = 20
    ) -> List[Pedido]:
        statement = (
            select(Pedido)
            .where(Pedido.estado_codigo == estado_codigo)
            .offset(offset)
            .limit(limit)
            .options(selectinload(Pedido.detalles))
            .order_by(Pedido.creado_en.desc())
        )
        return list(self.session.exec(statement).all())

    def count_activos_por_estado(self, estado_codigo: str) -> int:
        statement = (
            select(func.count(Pedido.id))
            .where(Pedido.estado_codigo == estado_codigo)
        )
        return self.session.exec(statement).one()

    # ====================================================================
    # 4. LISTAR PEDIDOS POR USUARIO
    # ====================================================================
    def get_all_activos_por_usuario(
        self, usuario_id: int, offset: int = 0, limit: int = 20
    ) -> List[Pedido]:
        statement = (
            select(Pedido)
            .where(Pedido.usuario_id == usuario_id)
            .offset(offset)
            .limit(limit)
            .options(selectinload(Pedido.detalles))
            .order_by(Pedido.creado_en.desc())
        )
        return list(self.session.exec(statement).all())

    def count_activos_por_usuario(self, usuario_id: int) -> int:
        statement = (
            select(func.count(Pedido.id))
            .where(Pedido.usuario_id == usuario_id)
        )
        return self.session.exec(statement).one()

    # ====================================================================
    # 5. LISTAR TODOS LOS PEDIDOS (INCLUYENDO ELIMINADOS SI HAY)
    # ====================================================================
    def get_all_incluyendo_eliminados(
        self, offset: int = 0, limit: int = 20
    ) -> List[Pedido]:
        """Para panel de administración."""
        statement = (
            select(Pedido)
            .offset(offset)
            .limit(limit)
            .options(selectinload(Pedido.detalles))
            .order_by(Pedido.creado_en.desc())
        )
        return list(self.session.exec(statement).all())

    def count_total(self) -> int:
        """Cuenta todos los pedidos sin filtros."""
        statement = select(func.count(Pedido.id))
        return self.session.exec(statement).one()

    # ====================================================================
    # 6. HISTORIAL DE ESTADOS
    # ====================================================================
    def get_historial_by_pedido(
        self, pedido_id: int
    ) -> List[HistorialEstadoPedido]:
        """Obtiene el historial completo de un pedido ordenado por fecha."""
        statement = (
            select(HistorialEstadoPedido)
            .where(HistorialEstadoPedido.pedido_id == pedido_id)
            .order_by(HistorialEstadoPedido.creado_en.asc())
        )
        return list(self.session.exec(statement).all())

    def add_historial(self, historial: HistorialEstadoPedido) -> HistorialEstadoPedido:
        """Persiste un registro de historial."""
        self.session.add(historial)
        self.session.flush()
        return historial

    # ====================================================================
    # 7. DETALLES DE PEDIDO
    # ====================================================================
    def add_detalle(self, detalle: DetallePedido) -> DetallePedido:
        """Persiste un detalle de pedido."""
        self.session.add(detalle)
        self.session.flush()
        return detalle

    def add_many_detalles(self, detalles: List[DetallePedido]) -> None:
        """Persiste múltiples detalles de pedido en batch."""
        for detalle in detalles:
            self.session.add(detalle)
        self.session.flush()