"""
Módulo: app/modules/usuarios/router.py
=======================================

Endpoints HTTP del módulo Usuarios. Patrón (siguiendo el modelo de
referencia):

  - El router depende del **Service** (no del UoW).
  - El Service se inyecta vía la factory `get_usuario_service`, que toma
    la session de la dependency `get_session` y construye el Service.
  - El Service internamente crea el UoW con `with ... as uow:`.

El router solo:
  - Define paths y status codes.
  - Parsea el body (vía Schemas de Pydantic).
  - Maneja cookies HttpOnly para el JWT.
  - Devuelve responses tipados con `response_model`.
"""

# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

# Config (para leer expiración del access token).
from app.core.config import settings

# Database dependency.
from app.core.database import get_session

# Auth dependencies.
from app.core.deps import get_current_user, require_role

# Schemas (DTOs).
from app.modules.usuarios.schemas import (
    Token,
    UserCreate,
    UserList,
    UserPublic,
    UserUpdate,
)

# Service (la capa de negocio).
from app.modules.usuarios.service import UsuarioService


# ---------------------------------------------------------------------------
# ROUTER
# ---------------------------------------------------------------------------
# `prefix` y `tags` se setean en main.py al include_router.
router = APIRouter(tags=["usuarios"])


# ---------------------------------------------------------------------------
# FACTORY: get_usuario_service
# ---------------------------------------------------------------------------
def get_usuario_service(
    session: Session = Depends(get_session),
) -> UsuarioService:
    """
    Factory: inyecta la sesión de BD en el Service.

    FastAPI la llama automáticamente en cada request que declare el
    Service como dependency. La `session` viene del `get_session` (que
    se cierra/commitea al terminar el request).

    Cada request obtiene su PROPIA instance de `UsuarioService` con su
    PROPIA session. No hay estado compartido entre requests.
    """
    return UsuarioService(session=session)


# ===========================================================================
# POST /usuarios/register
# ===========================================================================
@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un usuario nuevo",
    description=(
        "Crea un usuario nuevo. Público (no requiere auth). Username y "
        "email deben ser únicos. La contraseña se hashea con bcrypt."
    ),
)
def register(
    payload: UserCreate,
    svc: UsuarioService = Depends(get_usuario_service),
) -> UserPublic:
    """
    Endpoint de registro. El `payload` es validado por Pydantic
    (UserCreate) ANTES de llamar a la función. Si falta un campo o
    tiene formato inválido, Pydantic lanza 422.
    """
    return svc.register(payload)


# ===========================================================================
# POST /usuarios/token — Login OAuth2
# ===========================================================================
@router.post(
    "/token",
    summary="Iniciar sesión (OAuth2 form)",
    description=(
        "Autentica con username + password y devuelve un JWT. El token "
        "se devuelve en el body Y se setea como cookie HttpOnly para "
        "que el navegador lo envíe automáticamente en requests "
        "subsiguientes."
    ),
)
def login_for_access_token(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    svc: UsuarioService = Depends(get_usuario_service),
) -> dict:
    """
    Endpoint de login OAuth2 estándar.

    Acepta un **form** (no JSON) con `username` y `password`. Esto es
    lo que Swagger UI usa por defecto.

    El body de respuesta es un dict simple con un mensaje de éxito.
    El JWT viaja en la cookie `access_token`.
    """
    # Llamamos al Service. authenticate lanza AuthenticationError si falla,
    # que el exception_handler convierte a 401.
    token = svc.authenticate(form_data.username, form_data.password)

    # Seteamos el JWT como cookie HttpOnly. JS no puede accederla
    # (protección XSS); `samesite="lax"` mitiga CSRF.
    response.set_cookie(
        key="access_token",
        value=token.access_token,
        httponly=True,
        secure=False,  # True en producción (HTTPS)
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    return {"mensaje": "Login exitoso. Sesión iniciada."}


# ===========================================================================
# POST /usuarios/logout
# ===========================================================================
@router.post(
    "/logout",
    summary="Cerrar sesión",
    description="Elimina la cookie de autenticación. Idempotente.",
)
def logout(response: Response) -> dict:
    """
    Cierra la sesión del usuario borrando la cookie.

    NOTA: como el JWT es stateless, no podemos invalidarlo en el server
    sin un blacklist. Para producción real: refresh tokens con revocación
    o JWT blacklist con Redis.
    """
    response.delete_cookie(key="access_token", path="/")
    return {"mensaje": "Sesión cerrada exitosamente"}


# ===========================================================================
# GET /usuarios/me
# ===========================================================================
@router.get(
    "/me",
    response_model=UserPublic,
    summary="Obtener el usuario actual",
    description="Devuelve la información del usuario autenticado (del JWT).",
)
def read_users_me(
    current_user: UserPublic = Depends(get_current_user),
) -> UserPublic:
    """
    Endpoint "whoami". Devuelve el usuario que está logueado.

    La dependency `get_current_user`:
      1. Lee la cookie `access_token`.
      2. Decodifica el JWT.
      3. Busca al usuario en la DB.
      4. Verifica que esté activo.
      5. Lo inyecta como `current_user`.

    No necesita el Service: la info ya está en el dependency.
    """
    return current_user


# ===========================================================================
# GET /usuarios/ — listar (solo admin)
# ===========================================================================
@router.get(
    "/",
    response_model=UserList,
    summary="Listar usuarios (solo admin)",
    description="Lista paginada de usuarios. Solo admins.",
)
def list_users(
    skip: int = 0,
    limit: int = 100,
    svc: UsuarioService = Depends(get_usuario_service),
    # `require_role("admin")` valida que el usuario actual sea admin.
    # Si no, lanza 403. Usamos `= Depends(...)` (no Annotated) para que
    # Python no proteste por un param sin default después de params
    # con default.
    _admin: UserPublic = Depends(require_role(["admin"])),
) -> UserList:
    """Lista todos los usuarios con paginación. Solo admins."""
    return svc.list_all(skip=skip, limit=limit)


# ===========================================================================
# GET /usuarios/{user_id}
# ===========================================================================
@router.get(
    "/{user_id}",
    response_model=UserPublic,
    summary="Obtener un usuario por ID",
    description="Cualquier usuario autenticado puede ver el perfil de otro.",
)
def get_user(
    user_id: int,
    svc: UsuarioService = Depends(get_usuario_service),
    _current: UserPublic = Depends(get_current_user),
) -> UserPublic:
    """Devuelve un usuario por su ID. 404 si no existe."""
    return svc.get_by_id(user_id)


# ===========================================================================
# PATCH /usuarios/{user_id} — actualizar
# ===========================================================================
@router.patch(
    "/{user_id}",
    response_model=UserPublic,
    summary="Actualizar un usuario (parcial)",
    description=(
        "PATCH. Los campos no enviados no se modifican. Solo admins "
        "pueden cambiar is_active."
    ),
)
def update_user(
    user_id: int,
    payload: UserUpdate,
    svc: UsuarioService = Depends(get_usuario_service),
    current_user: UserPublic = Depends(get_current_user),
) -> UserPublic:
    """
    Actualización parcial. El Service valida reglas de autorización
    (solo admin cambia is_active, anti self-lockout).
    """
    return svc.update(user_id, payload, current_user)


# ===========================================================================
# POST /usuarios/admin/usuarios/{user_id}/activar
# POST /usuarios/admin/usuarios/{user_id}/desactivar
# ===========================================================================
@router.post(
    "/admin/usuarios/{user_id}/activar",
    response_model=UserPublic,
    summary="Activar un usuario (solo admin)",
)
def activate_user(
    user_id: int,
    svc: UsuarioService = Depends(get_usuario_service),
    _admin: UserPublic = Depends(require_role("admin")),
    current_user: UserPublic = Depends(get_current_user),
) -> UserPublic:
    """Reactivar un usuario desactivado. Solo admins."""
    return svc.set_active(user_id, is_active=True, current_user=current_user)


@router.post(
    "/admin/usuarios/{user_id}/desactivar",
    response_model=UserPublic,
    summary="Desactivar un usuario (solo admin)",
    description="Soft delete. No se puede desactivar a sí mismo.",
)
def deactivate_user(
    user_id: int,
    svc: UsuarioService = Depends(get_usuario_service),
    _admin: UserPublic = Depends(require_role(["admin"])),
    current_user: UserPublic = Depends(get_current_user),
) -> UserPublic:
    """Desactivar (soft delete) un usuario. Solo admins. Anti self-lockout."""
    return svc.set_active(user_id, is_active=False, current_user=current_user)
