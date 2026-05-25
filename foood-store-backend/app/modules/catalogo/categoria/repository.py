from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from typing import Sequence

from core.repository import BaseRepository
from .models import Categoria


class CategoriaRepository(BaseRepository[Categoria]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Categoria)

    def get_by_id(self, categoria_id: int) -> Categoria | None:
        """Busca por ID sin filtrar por eliminado_en."""
        return self.session.exec(
            select(Categoria)
            .options(selectinload(Categoria.subcategorias))
            .where(Categoria.id == categoria_id)
        ).first()

    def get_all_incluir_eliminados(
        self, skip: int = 0, limit: int = 200
    ) -> Sequence[Categoria]:
        """Todas las categorías (activas + eliminadas) para el panel admin."""
        return self.session.exec(
            select(Categoria)
            .options(selectinload(Categoria.subcategorias))
            .order_by(Categoria.parent_id, Categoria.nombre)
            .offset(skip)
            .limit(limit)
        ).all()

    def get_eliminado(self, categoria_id: int) -> Categoria | None:
        """Busca una categoría con soft-delete aplicado (para reactivación)."""
        return self.session.exec(
            select(Categoria)
            .options(selectinload(Categoria.subcategorias))
            .where(
                Categoria.id == categoria_id,
                Categoria.eliminado_en != None,  # noqa: E711
            )
        ).first()

    def get_activo(self, categoria_id: int) -> Categoria | None:
        return self.session.exec(
            select(Categoria)
            .options(selectinload(Categoria.subcategorias))
            .where(
                Categoria.id == categoria_id,
                Categoria.eliminado_en == None,  # noqa: E711
            )
        ).first()

    def get_all_raiz(self, skip: int = 0, limit: int = 20) -> Sequence[Categoria]:
        """Categorías raíz (sin padre) con sus hijos directos cargados."""
        return self.session.exec(
            select(Categoria)
            .options(selectinload(Categoria.subcategorias))
            .where(
                Categoria.parent_id == None,  # noqa: E711
                Categoria.eliminado_en == None,  # noqa: E711
            )
            .offset(skip)
            .limit(limit)
        ).all()

    def get_all_activos(self, skip: int = 0, limit: int = 20) -> Sequence[Categoria]:
        return self.session.exec(
            select(Categoria)
            .options(selectinload(Categoria.subcategorias))
            .where(Categoria.eliminado_en == None)  # noqa: E711
            .offset(skip)
            .limit(limit)
        ).all()

    def get_by_parent_id(
        self, parent_id: int, skip: int = 0, limit: int = 20
    ) -> Sequence[Categoria]:
        """Hijos directos de un nodo específico con paginación."""
        return self.session.exec(
            select(Categoria)
            .options(selectinload(Categoria.subcategorias))
            .where(
                Categoria.parent_id == parent_id,
                Categoria.eliminado_en == None,  # noqa: E711
            )
            .offset(skip)
            .limit(limit)
        ).all()

    def has_active_children(self, categoria_id: int) -> bool:
        """Devuelve True si la categoría tiene subcategorías activas (para bloquear eliminación)."""
        result = self.session.exec(
            select(Categoria)
            .where(
                Categoria.parent_id == categoria_id,
                Categoria.eliminado_en == None,  # noqa: E711
            )
        ).first()
        return result is not None

    def has_active_products(self, categoria_id: int) -> bool:
        """Devuelve True si la categoría tiene al menos un producto activo (para 409)."""
        # Import local para evitar circular en nivel de módulo
        from app.modules.catalogo.shared_models import ProductoCategoria
        from app.modules.catalogo.producto.models import Producto

        result = self.session.exec(
            select(ProductoCategoria)
            .join(Producto, Producto.id == ProductoCategoria.producto_id)
            .where(
                ProductoCategoria.categoria_id == categoria_id,
                Producto.eliminado_en == None,  # noqa: E711
            )
        ).first()
        return result is not None
