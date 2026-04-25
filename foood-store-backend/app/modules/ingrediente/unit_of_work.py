from sqlmodel import Session
from core.unit_of_work import UnitOfWork
from app.modules.ingrediente.repository import IngredienteRepository


class IngredienteUnitOfWork(UnitOfWork):
    """
    UoW del módulo ingrediente.
    Expone los repositorios que el servicio necesita coordinar
    bajo una misma transacción.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.ingredientes = IngredienteRepository(session)