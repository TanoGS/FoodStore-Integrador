from typing import Optional
from sqlmodel import Session, select
from core.repository import BaseRepository
from .models import Pago


class PagoRepository(BaseRepository[Pago]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Pago)

    def get_by_pedido_id(self, pedido_id: int) -> Optional[Pago]:
        return self.session.exec(
            select(Pago).where(Pago.pedido_id == pedido_id)
        ).first()

    def get_by_external_reference(self, external_ref: str) -> Optional[Pago]:
        return self.session.exec(
            select(Pago).where(Pago.external_reference == external_ref)
        ).first()
