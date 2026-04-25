from sqlmodel import Session
from core.unit_of_work import UnitOfWork
from app.modules.producto.repository import ProductoRepository
from app.modules.categoria.repository import CategoriaRepository
from app.modules.ingrediente.repository import IngredienteRepository


class ProductoUnitOfWork(UnitOfWork):
    """
    UoW del módulo producto.
    Expone ProductoRepository, CategoriaRepository e IngredienteRepository
    porque asignar categorías e ingredientes a un producto toca múltiples
    entidades en la misma transacción.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.productos = ProductoRepository(session)
        self.categorias = CategoriaRepository(session)    # cross-module, misma transacción
        self.ingredientes = IngredienteRepository(session)  # cross-module, misma transacción