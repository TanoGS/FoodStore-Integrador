from sqlmodel import Session, select
from core.repository import BaseRepository
from app.modules.producto.models import Producto


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
            select(Producto).where(Producto.nombre == nombre)
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