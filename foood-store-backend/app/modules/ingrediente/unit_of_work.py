from sqlmodel import Session
from .repository import IngredienteRepository

class IngredienteUnitOfWork:
    def __init__(self, session: Session):
        self.session = session
        self.ingredientes = IngredienteRepository(session)

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()