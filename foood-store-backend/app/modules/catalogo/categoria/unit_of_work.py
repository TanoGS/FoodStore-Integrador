from sqlmodel import Session

from core.unit_of_work import UnitOfWork
from .repository import CategoriaRepository


class CategoriaUnitOfWork(UnitOfWork):
    """
    UoW específico del módulo Categoria.
    No cierra la sesión en __exit__ porque FastAPI gestiona su ciclo de vida
    a través de la dependencia get_session().
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.categorias = CategoriaRepository(session)

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self._session.commit()
        else:
            self._session.rollback()
