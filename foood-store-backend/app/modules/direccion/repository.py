from sqlmodel import Session, select
from typing import List, Optional
from core.repository import BaseRepository
from .models import DireccionEntrega


class DireccionRepository(BaseRepository[DireccionEntrega]):
    def __init__(self, session: Session):
        super().__init__(session, DireccionEntrega)

    def get_by_id(self, direccion_id: int, usuario_id: int) -> Optional[DireccionEntrega]:
        """Busca una dirección activa por ID validando la propiedad del usuario."""
        return self.session.exec(
            select(DireccionEntrega).where(
                DireccionEntrega.id == direccion_id,
                DireccionEntrega.usuario_id == usuario_id,
                DireccionEntrega.eliminado_en == None,  # noqa: E711
            )
        ).first()

    def get_by_usuario(self, usuario_id: int) -> List[DireccionEntrega]:
        """Trae todas las direcciones activas de un usuario."""
        return list(self.session.exec(
            select(DireccionEntrega).where(
                DireccionEntrega.usuario_id == usuario_id,
                DireccionEntrega.eliminado_en == None,  # noqa: E711
            )
        ).all())

    def quitar_predeterminadas(self, usuario_id: int) -> None:
        """Pone predeterminada=False en todas las direcciones activas del usuario."""
        for d in self.get_by_usuario(usuario_id):
            d.predeterminada = False
            self.session.add(d)

    def get_eliminado_by_id(self, direccion_id: int, usuario_id: int) -> Optional[DireccionEntrega]:
        """Busca una dirección soft-deleted por ID validando la propiedad del usuario."""
        return self.session.exec(
            select(DireccionEntrega).where(
                DireccionEntrega.id == direccion_id,
                DireccionEntrega.usuario_id == usuario_id,
                DireccionEntrega.eliminado_en != None,  # noqa: E711
            )
        ).first()