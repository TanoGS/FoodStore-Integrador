from sqlmodel import Session, select
from typing import Optional, List
from .models import Ingrediente

class IngredienteRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, ingrediente: Ingrediente) -> Ingrediente:
        self.session.add(ingrediente)
        return ingrediente

    def get_by_id(self, id: int) -> Optional[Ingrediente]:
        return self.session.get(Ingrediente, id)

    def get_by_nombre(self, nombre: str) -> Optional[Ingrediente]:
        statement = select(Ingrediente).where(Ingrediente.nombre == nombre)
        return self.session.exec(statement).first()

    def get_all_activos(self) -> List[Ingrediente]:
        statement = select(Ingrediente).where(Ingrediente.eliminado_en == None)
        return self.session.exec(statement).all()