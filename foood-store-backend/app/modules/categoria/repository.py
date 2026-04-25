from sqlmodel import Session, select
from core.repository import BaseRepository
from app.modules.categoria.models import Categoria


class CategoriaRepository(BaseRepository[Categoria]):
    """
    Repositorio de Categoria.
    Agrega queries específicas del dominio sobre el CRUD base.
    Solo habla con la DB — nunca levanta HTTPException.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session, Categoria)

    def get_by_nombre(self, nombre: str) -> Categoria | None:
        return self.session.exec(
            select(Categoria).where(
                Categoria.nombre == nombre,
                Categoria.eliminado_en == None,  # noqa: E711
            )
        ).first()

    def get_all_activas(self, offset: int = 0, limit: int = 20) -> list[Categoria]:
        return list(
            self.session.exec(
                select(Categoria)
                .where(Categoria.eliminado_en == None)  # noqa: E711
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def count_activas(self) -> int:
        return len(
            self.session.exec(
                select(Categoria).where(Categoria.eliminado_en == None)  # noqa: E711
            ).all()
        )

    def get_subcategorias(self, padre_id: int) -> list[Categoria]:
        """Devuelve los hijos directos activos de una categoría."""
        return list(
            self.session.exec(
                select(Categoria)
                .where(
                    Categoria.padre_id == padre_id,
                    Categoria.eliminado_en == None,  # noqa: E711
                )
            ).all()
        )