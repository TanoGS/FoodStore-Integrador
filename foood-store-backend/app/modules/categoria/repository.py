from sqlmodel import Session, select
from typing import Optional, List
from .models import Categoria

class CategoriaRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, categoria: Categoria) -> Categoria:
        self.session.add(categoria)
        return categoria

    def get_by_id(self, id: int) -> Optional[Categoria]:
        return self.session.get(Categoria, id)

    def get_by_nombre(self, nombre: str) -> Optional[Categoria]:
        statement = select(Categoria).where(Categoria.nombre == nombre)
        return self.session.exec(statement).first()

    def get_all_activas(self) -> List[Categoria]:
        # Trae solo las categorías que no han sido eliminadas lógicamente
        statement = select(Categoria).where(Categoria.eliminado_en == None)
        return self.session.exec(statement).all()