from sqlmodel import Session, select
from typing import Optional, List
from .models import Producto

class ProductoRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, producto: Producto):
        self.session.add(producto)

    def get_by_id(self, id: int) -> Optional[Producto]:
        return self.session.get(Producto, id)

    def get_by_nombre(self, nombre: str) -> Optional[Producto]:
        return self.session.exec(select(Producto).where(Producto.nombre == nombre)).first()

    def get_all_activos(self) -> List[Producto]:
        return self.session.exec(
            select(Producto).where(Producto.eliminado_en == None, Producto.activo == True)
        ).all()