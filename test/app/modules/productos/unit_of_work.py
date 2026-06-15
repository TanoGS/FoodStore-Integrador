"""
Módulo: app/modules/productos/unit_of_work.py
==============================================

Unit of Work del módulo Productos (refactorizado al patrón del modelo).
"""

from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.productos.repository import ProductoRepository


class ProductoUnitOfWork(UnitOfWork):
    """
    UoW de Productos. Expone `self.productos` (ProductoRepository)
    construido sobre la misma session.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.productos = ProductoRepository(session)
