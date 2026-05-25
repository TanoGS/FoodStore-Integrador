from sqlmodel import Session
from core.unit_of_work import UnitOfWork
from .repository import PedidoRepository


class PedidoUnitOfWork(UnitOfWork):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.pedidos = PedidoRepository(session)
