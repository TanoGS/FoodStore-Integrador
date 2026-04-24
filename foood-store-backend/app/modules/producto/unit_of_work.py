from sqlmodel import Session
from .repository import ProductoRepository
from app.modules.categoria.repository import CategoriaRepository

class ProductoUnitOfWork:
    def __init__(self, session: Session):
        self.session = session
        self.productos = ProductoRepository(session)
        self.categorias = CategoriaRepository(session)
        
    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()