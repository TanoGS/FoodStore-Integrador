from sqlmodel import Session, select
from core.repository import BaseRepository
from app.modules.producto.models import Producto, ProductoIngrediente


class ProductoRepository(BaseRepository[Producto]):
    """
    Repositorio de Producto.
    Agrega queries específicas del dominio sobre el CRUD base.
    Solo habla con la DB — nunca levanta HTTPException.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session, Producto)

    def get_by_nombre(self, nombre: str) -> Producto | None:
        return self.session.exec(
            select(Producto).where(
                Producto.nombre == nombre,
                Producto.eliminado_en == None,  # noqa: E711
            )
        ).first()

    def get_all_activos(self, offset: int = 0, limit: int = 20) -> list[Producto]:
        return list(
            self.session.exec(
                select(Producto)
                .where(
                    Producto.eliminado_en == None,  # noqa: E711
                    Producto.activo == True,  # noqa: E712
                )
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def count_activos(self) -> int:
        return len(
            self.session.exec(
                select(Producto)
                .where(
                    Producto.eliminado_en == None,  # noqa: E711
                    Producto.activo == True,  # noqa: E712
                )
            ).all()
        )

    # ── Asociación Producto-Ingrediente ────────────────────────────────────────

    def get_relaciones_ingredientes(self, producto_id: int) -> list[ProductoIngrediente]:
        """Devuelve todas las asociaciones de ingredientes para un producto."""
        return list(
            self.session.exec(
                select(ProductoIngrediente)
                .where(ProductoIngrediente.producto_id == producto_id)
            ).all()
        )

    def get_relacion_ingrediente(
        self, producto_id: int, ingrediente_id: int
    ) -> ProductoIngrediente | None:
        """Busca la asociación específica entre un producto y un ingrediente."""
        return self.session.exec(
            select(ProductoIngrediente).where(
                ProductoIngrediente.producto_id == producto_id,
                ProductoIngrediente.ingrediente_id == ingrediente_id,
            )
        ).first()

    def add_relacion_ingrediente(self, relacion: ProductoIngrediente) -> ProductoIngrediente:
        """Persiste la asociación producto-ingrediente en la sesión."""
        self.session.add(relacion)
        self.session.flush()
        self.session.refresh(relacion)
        return relacion