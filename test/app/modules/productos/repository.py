"""
Módulo: app/modules/productos/repository.py
============================================

Repository específico de Productos (refactorizado al patrón del
modelo: session en self, sin pasarla por parámetro).
"""

from sqlmodel import Session, func, select

from app.core.base_repository import BaseRepository
from app.modules.productos.models import Producto


class ProductoRepository(BaseRepository[Producto]):
    """
    Repository de Producto. CRUD base + queries de dominio:
      - get_by_nombre(nombre): para validar unicidad exacta.
      - search(...): búsqueda con filtros opcionales + paginación.
      - count_active(): total de productos activos.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(Producto, session)

    def get_by_nombre(self, nombre: str) -> Producto | None:
        """Búsqueda exacta por nombre (case-sensitive)."""
        statement = select(Producto).where(Producto.nombre == nombre)
        return self.session.exec(statement).first()

    def search(
        self,
        nombre: str | None = None,
        categoria: str | None = None,
        min_precio: float | None = None,
        max_precio: float | None = None,
        skip: int = 0,
        limit: int = 100,
        only_active: bool = True,
    ) -> list[Producto]:
        """
        Búsqueda con filtros combinables. Todos los filtros son opcionales.

        `is_(None)` en los `where` para que un filtro None no agregue
        condición (no es lo mismo "filtra por X=None" que "no filtres").
        """
        statement = select(Producto)

        if nombre is not None:
            # `ilike` = case-insensitive LIKE. `%` wildcards.
            statement = statement.where(Producto.nombre.ilike(f"%{nombre}%"))
        if categoria is not None:
            statement = statement.where(Producto.categoria == categoria)
        if min_precio is not None:
            statement = statement.where(Producto.precio >= min_precio)
        if max_precio is not None:
            statement = statement.where(Producto.precio <= max_precio)
        if only_active:
            statement = statement.where(Producto.is_active.is_(True))

        statement = statement.order_by(Producto.id).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

    def count_active(self) -> int:
        """Cuenta productos activos (para `total` en paginación)."""
        statement = (
            select(func.count())
            .select_from(Producto)
            .where(Producto.is_active.is_(True))
        )
        return self.session.scalar(statement) or 0

    def count_search(
        self,
        nombre: str | None = None,
        categoria: str | None = None,
        min_precio: float | None = None,
        max_precio: float | None = None,
        only_active: bool = True,
    ) -> int:
        """
        Cuenta los productos que matchean los mismos filtros que `search`.
        Para que el `total` en la respuesta paginada sea coherente.
        """
        statement = select(func.count()).select_from(Producto)

        if nombre is not None:
            statement = statement.where(Producto.nombre.ilike(f"%{nombre}%"))
        if categoria is not None:
            statement = statement.where(Producto.categoria == categoria)
        if min_precio is not None:
            statement = statement.where(Producto.precio >= min_precio)
        if max_precio is not None:
            statement = statement.where(Producto.precio <= max_precio)
        if only_active:
            statement = statement.where(Producto.is_active.is_(True))

        return self.session.scalar(statement) or 0
