# =============================================================================
# deps.py — Dependencias de FastAPI (autenticación y autorización)
# =============================================================================
#
# CONCEPTO CLAVE: Dependency Injection en FastAPI
# ----------------------------------------------------
# FastAPI resuelve dependencias ANTES de ejecutar el endpoint. Esto permite:
#   1. Inyectar servicios (repos, UoW, sesiones).
#   2. Encadenar validaciones (auth → activo → rol).
#   3. Reutilizar lógica entre endpoints.
#
# CONVENCIONES HTTP (estándar REST):
#   - 401 Unauthorized: el cliente NO está autenticado (token inválido/ausente).
#   - 403 Forbidden: el cliente está autenticado pero NO tiene permisos.
# =============================================================================

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import decode_access_token
from app.core.logger import get_logger
from app.modules.usuarios.schemas import UserPublic
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork

# Logger del módulo para auditoría de intentos de autenticación.
logger = get_logger(__name__)


class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    """
    Variante de OAuth2PasswordBearer que extrae el token de la COOKIE HttpOnly.

    ¿POR QUÉ COOKIE Y NO HEADER?
    ----------------------------------------------------
    - El frontend JavaScript NO puede leer cookies HttpOnly (mitiga XSS):
      un atacante que inyecta JS en la página no puede robar el token.
    - SameSite=lax previene CSRF: el navegador solo envía la cookie si el
      request viene del mismo sitio.
    - El navegador envía la cookie AUTOMÁTICAMENTE en cada request al backend.

    Trade-off: las cookies requieren un dominio bien configurado y HTTPS en
    producción (secure=True) para que viajen encriptadas.
    """

    async def __call__(self, request: Request) -> str | None:
        # 1) Lee la cookie "access_token" (debe haber sido seteada en el login).
        token = request.cookies.get("access_token")

        # 2) Si no hay cookie, opcionalmente revisa el header Authorization.
        # Está comentado por seguridad: si permitimos ambos, un atacante con
        # XSS podría mandar el token por header sin pasar por la cookie.
        #
        # if not token:
        #     auth_header = request.headers.get("Authorization")
        #     if auth_header and auth_header.startswith("Bearer "):
        #         token = auth_header.split(" ", 1)[1]

        # 3) Si no hay token en ningún lado:
        if not token:
            if self.auto_error:
                # auto_error=True (default) → lanza 401 automáticamente.
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No autenticado",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        return token


# Instancia global del esquema OAuth2.
# tokenUrl apunta al endpoint de login (necesario para OpenAPI / Swagger UI).
oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="/api/v1/auth/token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> UserPublic:
    """
    Decodifica el JWT, valida, y retorna el usuario autenticado.

    Esta es la dependencia RAÍZ del flujo de autenticación. Sobre ella se
    construyen get_current_active_user y require_role.

    Raises:
        HTTPException 401: token inválido, expirado, o usuario inexistente.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1) Decodificar y validar firma + expiración.
    payload = decode_access_token(token)
    if payload is None:
        logger.warning("Intento de acceso con token inválido")
        raise credentials_exception

    # 2) Extraer el "sub" (subject = username en nuestro caso).
    username: str | None = payload.get("sub")
    if username is None:
        logger.warning("Token sin claim 'sub'")
        raise credentials_exception

    # 3) Buscar el usuario en BD. El token puede ser válido pero el usuario
    # puede haber sido eliminado o desactivado después de emitirlo.
    with UsuarioUnitOfWork(session) as uow:
        user = uow.usuarios.get_by_username(username)
        if user is None:
            logger.warning(f"Token válido pero usuario '{username}' no existe en BD")
            raise credentials_exception

        # Convierte el modelo SQLModel al schema público (sin hashed_password).
        return UserPublic.model_validate(user)


async def get_current_active_user(
    current_user: Annotated[UserPublic, Depends(get_current_user)],
) -> UserPublic:
    """
    Verifica que el usuario autenticado esté ACTIVO (no desactivado).

    Encadena sobre get_current_user: primero valida el token, después el estado.
    """
    if not current_user.is_active:
        logger.warning(f"Usuario '{current_user.username}' intentó operar pero está desactivado")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cuenta de usuario desactivada",
        )
    return current_user


def require_role(allowed_roles: list[str]):
    """
    Factory de dependencias para RBAC (Role-Based Access Control).

    Uso típico:
        @router.get("/admin", dependencies=[Depends(require_role(["admin"]))])
        async def admin_only():
            ...

    O como parámetro del endpoint:
        async def admin_only(
            admin: Annotated[UserPublic, Depends(require_role(["admin"]))],
        ):
            ...

    La comparación es case-insensitive para tolerar inconsistencias
    entre el token (que puede venir en mayúsculas) y la BD.

    Returns:
        Una dependencia lista para usar con Depends().
    """

    async def role_checker(
        current_user: Annotated[UserPublic, Depends(get_current_active_user)],
    ) -> UserPublic:
        user_role_normalized = current_user.rol.upper().strip()

        if user_role_normalized not in [r.upper() for r in allowed_roles]:
            logger.warning(
                f"Acceso denegado: usuario '{current_user.username}' "
                f"(rol='{current_user.rol}') intentó acceder a recurso que requiere {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Permisos insuficientes. Tu rol es '{current_user.rol}'. "
                    f"Se requiere uno de: {allowed_roles}"
                ),
            )
        return current_user

    return role_checker
