from sqlmodel import Session

from core.unit_of_work import UnitOfWork
from .repository import IngredienteRepository


class IngredienteUnitOfWork(UnitOfWork):
    """
    UoW específico del módulo Ingrediente.
    No cierra la sesión en __exit__: FastAPI gestiona su ciclo de vida.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.ingredientes = IngredienteRepository(session)

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self._session.commit()
        else:
            self._session.rollback()
