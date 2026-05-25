from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlmodel import Session, select

from core.config import settings
from core.database import get_session
from app.modules.usuario.models import Usuario

_bearer = HTTPBearer()


def _decode_token(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    """Decodifica el JWT y devuelve el payload. Lanza 401 si es inválido."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    payload: Annotated[dict, Depends(_decode_token)],
    session: Session = Depends(get_session),
) -> Usuario:
    """Devuelve el Usuario activo correspondiente al token."""
    usuario_id: str | None = payload.get("sub")
    if not usuario_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin sujeto.")

    usuario = session.get(Usuario, int(usuario_id))
    if not usuario or usuario.eliminado_en is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo.",
        )
    return usuario


def require_roles(*roles: str):
    """
    Factory que devuelve una dependencia FastAPI que verifica que el usuario
    autenticado tenga AL MENOS UNO de los roles indicados.

    Uso:
        @router.get("/admin", dependencies=[Depends(require_roles("ADMIN"))])
    """
    def _check(payload: Annotated[dict, Depends(_decode_token)]) -> dict:
        token_roles: list[str] = payload.get("roles", [])
        if not any(r in token_roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere uno de estos roles: {', '.join(roles)}.",
            )
        return payload

    return _check
