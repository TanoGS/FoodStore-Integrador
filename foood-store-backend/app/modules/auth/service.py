from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlmodel import Session, select

from app.modules.usuario.models import Usuario, UsuarioRol
from app.modules.rol.models import Rol
from app.modules.auth.schemas import LoginRequest, TokenResponse
from core.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def _get_roles_del_usuario(session: Session, usuario_id: int) -> list[str]:
    """Retorna la lista de nombres de rol activos para un usuario."""
    stmt = (
        select(Rol.nombre)
        .join(UsuarioRol, UsuarioRol.rol_id == Rol.id)
        .where(UsuarioRol.usuario_id == usuario_id)
    )
    return list(session.exec(stmt).all())


def _create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


class AuthService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def login(self, data: LoginRequest) -> TokenResponse:
        # 1. Buscar usuario activo por email
        usuario = self._session.exec(
            select(Usuario).where(
                Usuario.email == data.email,
                Usuario.eliminado_en == None,  # noqa: E711
            )
        ).first()

        if not usuario or not _verify_password(data.password, usuario.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 2. Obtener roles del usuario
        roles = _get_roles_del_usuario(self._session, usuario.id)

        # 3. Crear JWT con sub=email y roles embebidos
        token = _create_access_token({
            "sub": str(usuario.id),
            "email": usuario.email,
            "roles": roles,
        })

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            usuario_id=usuario.id,
            nombre=f"{usuario.nombre} {usuario.apellido}",
            roles=roles,
        )
