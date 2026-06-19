import datetime
from sqlmodel import Session, select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from core.repository import BaseRepository
from .models import Usuario, UsuarioRol, Rol
from typing import Optional

class UsuarioRepository(BaseRepository[Usuario]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Usuario)

    def get_by_email(self, email: str) -> Optional[Usuario]:
        #  ACTUALIZADO: Trae el usuario, sus enlaces intermedios y el objeto Rol final en un solo viaje limpio a la BD
        statement = (
            select(Usuario)
            .where(Usuario.email == email, Usuario.eliminado_en == None)
            .options(
                selectinload(Usuario.roles_enlaces)
                .selectinload(UsuarioRol.rol)
                .selectinload(Rol.permisos)
            )
        )
        return self.session.exec(statement).first()

    def get_all_activos(self, offset: int = 0, limit: int = 20) -> list[Usuario]:
        statement = (
            select(Usuario)
            .where(Usuario.eliminado_en == None)
            .offset(offset)
            .limit(limit)
            .options(
                selectinload(Usuario.roles_enlaces).selectinload(UsuarioRol.rol)
            )
        )
        return list(self.session.exec(statement).all())

    def count_activos(self) -> int:
        return len(self.session.exec(
            select(Usuario).where(Usuario.eliminado_en == None)
        ).all())
    
    def get_all_incluyendo_eliminados(self, offset: int = 0, limit: int = 20) -> list[Usuario]:
        statement = (
            select(Usuario)
            .offset(offset)
            .limit(limit)
            .options(
                selectinload(Usuario.roles_enlaces).selectinload(UsuarioRol.rol)
            )
        )
        return list(self.session.exec(statement).all())

    def count_total(self) -> int:
        return len(self.session.exec(select(Usuario)).all())
    
    def eliminar_usuario(self, usuario: Usuario):
        usuario.eliminado_en = datetime.datetime.utcnow()
        usuario.activo = False 
        self.session.add(usuario)

    def get_all_activos_por_rol(self, rol: str, offset: int = 0, limit: int = 20) -> list[Usuario]:
        statement = (
            select(Usuario)
            .join(UsuarioRol, Usuario.id == UsuarioRol.usuario_id)
            .where(
                Usuario.eliminado_en == None,  # noqa: E711
                UsuarioRol.rol_codigo == rol,
            )
            .offset(offset)
            .limit(limit)
            .options(selectinload(Usuario.roles_enlaces).selectinload(UsuarioRol.rol))
        )
        return list(self.session.exec(statement).unique().all())

    def count_activos_por_rol(self, rol: str) -> int:
        statement = (
            select(func.count(Usuario.id))
            .join(UsuarioRol, Usuario.id == UsuarioRol.usuario_id)
            .where(
                Usuario.eliminado_en == None,  # noqa: E711
                UsuarioRol.rol_codigo == rol,
            )
        )
        return self.session.exec(statement).one()

    def get_by_id_with_roles(self, usuario_id: int) -> Optional[Usuario]:
        """Obtiene un usuario por ID con sus roles cargados eagerly."""
        statement = (
            select(Usuario)
            .where(Usuario.id == usuario_id)
            .options(selectinload(Usuario.roles_enlaces).selectinload(UsuarioRol.rol))
        )
        return self.session.exec(statement).first()

    def get_all_with_roles(self) -> list[Usuario]:
        """Obtiene todos los usuarios con sus roles cargados."""
        statement = select(Usuario).options(
            selectinload(Usuario.roles_enlaces).selectinload(UsuarioRol.rol)
        )
        return list(self.session.exec(statement).unique().all())

    def get_refresh_token_by_hash(self, token_hash: str) -> Optional["RefreshToken"]:
        from .models import RefreshToken
        return self.session.exec(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).first()

    def add_refresh_token(self, refresh_token: "RefreshToken") -> None:
        self.session.add(refresh_token)

    def rol_existe(self, codigo: str) -> bool:
        return self.session.exec(select(Rol).where(Rol.codigo == codigo)).first() is not None