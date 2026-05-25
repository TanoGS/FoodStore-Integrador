from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from typing import Optional, Sequence

from core.repository import BaseRepository
from .models import Producto
from app.modules.catalogo.shared_models import ProductoIngrediente, ProductoCategoria


def _base_select():
    """Select con todas las relaciones precargadas."""
    return (
        select(Producto)
        .options(
            selectinload(Producto.categorias),
            selectinload(Producto.ingredientes_enlaces).selectinload(
                ProductoIngrediente.ingrediente
            ),
        )
    )


class ProductoRepository(BaseRepository[Producto]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Producto)

    def get_by_id(self, producto_id: int) -> Producto | None:
        """Busca por ID sin filtrar por eliminado_en (usado para reactivar)."""
        return self.session.exec(
            _base_select().where(Producto.id == producto_id)
        ).first()

    def get_activo(self, producto_id: int) -> Producto | None:
        return self.session.exec(
            _base_select().where(
                Producto.id == producto_id,
                Producto.eliminado_en == None,  # noqa: E711
            )
        ).first()

    def get_all_activos(self) -> Sequence[Producto]:
        return (
            self.session.exec(
                _base_select().where(Producto.eliminado_en == None)  # noqa: E711
            )
            .unique()
            .all()
        )

    def get_all_incluir_eliminados(
        self, skip: int = 0, limit: int = 200
    ) -> Sequence[Producto]:
        """Todos los productos (activos + eliminados) para el panel admin."""
        return (
            self.session.exec(
                _base_select()
                .order_by(Producto.eliminado_en, Producto.nombre)
                .offset(skip)
                .limit(limit)
            )
            .unique()
            .all()
        )

    def get_filtrado(
        self,
        categoria_id: Optional[int] = None,
        activo: Optional[bool] = None,
        q: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[Producto]:
        stmt = _base_select().where(Producto.eliminado_en == None)  # noqa: E711

        if categoria_id is not None:
            stmt = stmt.join(
                ProductoCategoria,
                ProductoCategoria.producto_id == Producto.id,
            ).where(ProductoCategoria.categoria_id == categoria_id)

        if activo is not None:
            stmt = stmt.where(Producto.activo == activo)

        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                Producto.nombre.ilike(like) | Producto.descripcion.ilike(like)
            )

        stmt = stmt.offset(skip).limit(limit)
        return self.session.exec(stmt).unique().all()
