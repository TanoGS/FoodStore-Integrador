from sqlmodel import Session, select
from typing import Optional, List
from .models import Producto, ProductoCategoria

class ProductoRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, producto: Producto) -> Producto:
        self.session.add(producto)
        return producto

    def get_by_id(self, id: int) -> Optional[Producto]:
        return self.session.get(Producto, id)

    def get_by_nombre(self, nombre: str) -> Optional[Producto]:
        statement = select(Producto).where(Producto.nombre == nombre)
        return self.session.exec(statement).first()

    def get_all_activos(self) -> List[Producto]:
        statement = select(Producto).where(Producto.eliminado_en == None, Producto.activo == True)
        return self.session.exec(statement).all()

    def asociar_categorias(self, producto_id: int, categoria_ids: List[int]):
        for cat_id in categoria_ids:
            relacion = ProductoCategoria(producto_id=producto_id, categoria_id=cat_id)
            self.session.add(relacion)