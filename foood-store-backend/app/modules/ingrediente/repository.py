from sqlmodel import Session, select
from core.repository import BaseRepository
from app.modules.ingrediente.models import Ingrediente


class IngredienteRepository(BaseRepository[Ingrediente]):
    """
    Repositorio de Ingrediente.
    Agrega queries específicas del dominio sobre el CRUD base.
    Solo habla con la DB — nunca levanta HTTPException.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session, Ingrediente)

    def get_by_nombre(self, nombre: str) -> Ingrediente | None:
        return self.session.exec(
            select(Ingrediente).where(
                Ingrediente.nombre == nombre,
                Ingrediente.eliminado_en == None,  # noqa: E711
            )
        ).first()

    def get_all_activos(self, offset: int = 0, limit: int = 20) -> list[Ingrediente]:
        return list(
            self.session.exec(
                select(Ingrediente)
                .where(Ingrediente.eliminado_en == None)  # noqa: E711
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def count_activos(self) -> int:
        return len(
            self.session.exec(
                select(Ingrediente)
                .where(Ingrediente.eliminado_en == None)  # noqa: E711
            ).all()
        )