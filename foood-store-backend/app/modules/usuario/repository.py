from sqlmodel import Session, select
from typing import List, Optional
from .models import Usuario

class UsuarioRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, usuario: Usuario) -> Usuario:
        self.session.add(usuario)
        return usuario

    def get_by_email(self, email: str) -> Optional[Usuario]:
        statement = select(Usuario).where(Usuario.email == email)
        return self.session.exec(statement).first()
    
    def get_by_id(self, id: int) -> Optional[Usuario]:
        return self.session.get(Usuario, id)

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Usuario]:
        statement = select(Usuario).offset(skip).limit(limit)
        return self.session.exec(statement).all()
    
    def get_activos(self, skip: int = 0, limit: int = 100) -> List[Usuario]:
        """Trae solo los usuarios donde activo == True."""
        statement = select(Usuario).where(Usuario.activo == True).offset(skip).limit(limit)
        return self.session.exec(statement).all()

    def get_eliminados(self, skip: int = 0, limit: int = 100) -> List[Usuario]:
        """Trae solo los usuarios donde activo == False (Soft Delete)."""
        statement = select(Usuario).where(Usuario.activo == False).offset(skip).limit(limit)
        return self.session.exec(statement).all()