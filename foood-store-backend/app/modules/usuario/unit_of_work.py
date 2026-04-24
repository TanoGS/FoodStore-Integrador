from sqlmodel import Session
from .repository import UsuarioRepository

class UsuarioUnitOfWork:
    def __init__(self, session: Session):
        self.session = session
        self.usuarios = UsuarioRepository(session)

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()