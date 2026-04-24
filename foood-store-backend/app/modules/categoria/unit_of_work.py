from sqlmodel import Session
from .repository import CategoriaRepository

class CategoriaUnitOfWork:
    def __init__(self, session: Session):
        self.session = session
        # Instanciamos el repositorio inyectándole la sesión actual
        self.categorias = CategoriaRepository(session)

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()