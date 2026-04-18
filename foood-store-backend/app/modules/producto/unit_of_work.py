from sqlmodel import Session
from .repository import ProductoRepository

class ProductoUnitOfWork:
    def __init__(self, session: Session):
        self.session = session
        self.productos = ProductoRepository(session)

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()