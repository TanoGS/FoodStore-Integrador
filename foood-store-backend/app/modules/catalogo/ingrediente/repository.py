from sqlmodel import Session, select
from typing import Sequence

from core.repository import BaseRepository
from .models import Ingrediente


class IngredienteRepository(BaseRepository[Ingrediente]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Ingrediente)

    def get_by_id(self, ingrediente_id: int) -> Ingrediente | None:
        """Busca por ID sin filtrar por eliminado_en (usado para reactivar)."""
        return self.session.exec(
            select(Ingrediente).where(Ingrediente.id == ingrediente_id)
        ).first()

    def get_activo(self, ingrediente_id: int) -> Ingrediente | None:
        return self.session.exec(
            select(Ingrediente).where(
                Ingrediente.id == ingrediente_id,
                Ingrediente.eliminado_en == None,  # noqa: E711
            )
        ).first()

    def get_all_activos(self, offset: int = 0, limit: int = 50) -> Sequence[Ingrediente]:
        return self.session.exec(
            select(Ingrediente)
            .where(Ingrediente.eliminado_en == None)  # noqa: E711
            .offset(offset)
            .limit(limit)
        ).all()

    def get_all_incluir_eliminados(self, offset: int = 0, limit: int = 200) -> Sequence[Ingrediente]:
        """Devuelve todos los ingredientes (activos + eliminados) para el panel admin."""
        return self.session.exec(
            select(Ingrediente)
            .order_by(Ingrediente.eliminado_en)  # activos primero (NULL < fecha)
            .offset(offset)
            .limit(limit)
        ).all()
