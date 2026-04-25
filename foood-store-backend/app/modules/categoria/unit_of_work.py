from sqlmodel import Session
from core.unit_of_work import UnitOfWork
from app.modules.categoria.repository import CategoriaRepository


class CategoriaUnitOfWork(UnitOfWork):
    """
    UoW del módulo categoria.
    Expone los repositorios que el servicio necesita coordinar
    bajo una misma transacción.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.categorias = CategoriaRepository(session)