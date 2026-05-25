from typing import Optional
from sqlmodel import Session
from core.repository import BaseRepository
from .models import Pedido


class PedidoRepository(BaseRepository[Pedido]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Pedido)

    def get_by_id_o_none(self, pedido_id: int) -> Optional[Pedido]:
        return self.session.get(Pedido, pedido_id)

