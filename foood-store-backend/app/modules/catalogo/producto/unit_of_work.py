from sqlmodel import Session

from core.unit_of_work import UnitOfWork
from .repository import ProductoRepository
from app.modules.catalogo.categoria.repository import CategoriaRepository
from app.modules.catalogo.ingrediente.repository import IngredienteRepository


class ProductoUnitOfWork(UnitOfWork):
    """
    UoW del módulo Producto (aggregate root del Dominio 2).
    Mantiene acceso a los repositorios de Categoria e Ingrediente
    para validar relaciones al crear/actualizar productos.
    No cierra la sesión en __exit__: FastAPI gestiona su ciclo de vida.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.productos = ProductoRepository(session)
        self.categorias = CategoriaRepository(session)
        self.ingredientes = IngredienteRepository(session)

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self._session.commit()
        else:
            self._session.rollback()
