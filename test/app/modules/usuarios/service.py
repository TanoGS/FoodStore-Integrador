"""
Módulo: app/modules/usuarios/service.py
========================================

Lógica de negocio del módulo Usuarios.

Patrón (siguiendo el modelo de referencia):
-------------------------------------------
El Service:
  - Recibe la `session` en su `__init__` (inyectada por FastAPI).
  - Por cada método de negocio, abre un UoW con `with UoW(self._session)`.
  - Dentro del with, usa los repositorios del UoW.
  - Al salir del with: commit automático si todo OK, rollback si excepción.

NO conoce FastAPI: no importa `Request`, `Response`, `HTTPException`.
Lanza **excepciones de dominio** que los exception_handlers convierten
a JSON con el formato estándar.
"""

# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
from datetime import datetime

from sqlmodel import Session

# Excepciones de dominio (formato JSON estándar vía exception_handlers).
from app.core.exceptions.custom_exceptions import (
    AuthenticationError,
    AuthorizationError,
    DuplicateResourceError,
    ResourceNotFoundError,
)

# Funciones de seguridad (hashing + JWT).
from app.core.security import create_access_token, hash_password, verify_password

# Modelo (tabla) y schemas (DTOs).
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.schemas import (
    Token,
    UserCreate,
    UserList,
    UserLogin,
    UserPublic,
    UserUpdate,
)

# Unit of Work del módulo.
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork


class UsuarioService:
    """
    Lógica de negocio del módulo Usuarios.

    El Service recibe la session en su constructor. Cada método abre
    SU PROPIO UoW con `with UsuarioUnitOfWork(self._session) as uow:`,
    garantizando que cada operación de negocio sea una transacción
    independiente y atómica.
    """

    def __init__(self, session: Session) -> None:
        """
        Args:
            session: la sesión activa de SQLAlchemy/SQLModel.
                     La inyecta el router vía la factory `get_usuario_service`.
        """
        # La guardamos como "privada". Cada método crea un UoW nuevo
        # sobre esta session.
        self._session = session

    # =======================================================================
    # register: crear un usuario nuevo
    # =======================================================================
    def register(self, payload: UserCreate) -> UserPublic:
        """
        Registra un usuario nuevo.

        Flujo:
          1. Verificar que el username NO exista.
          2. Verificar que el email NO exista.
          3. Hashear la contraseña con bcrypt.
          4. Crear el objeto `Usuario` y persistirlo.
          5. Devolver el `UserPublic` (sin hash).

        Raises:
            DuplicateResourceError: si username o email ya existen.
        """
        # Abrimos el UoW. Al salir del with: commit si todo OK.
        with UsuarioUnitOfWork(self._session) as uow:
            # --- 1. Validar username único -----------------------------------
            if uow.usuarios.get_by_username(payload.username):
                raise DuplicateResourceError(
                    resource="usuario",
                    field="username",
                    value=payload.username,
                )

            # --- 2. Validar email único --------------------------------------
            if uow.usuarios.get_by_email(payload.email):
                raise DuplicateResourceError(
                    resource="usuario",
                    field="email",
                    value=payload.email,
                )

            # --- 3. Hashear la contraseña ------------------------------------
            # `hash_password` aplica bcrypt con un salt aleatorio.
            # Resultado: string tipo "$2b$12$..." (60 chars aprox).
            hashed = hash_password(payload.password)

            # --- 4. Construir y persistir el Usuario -------------------------
            # ⚠️ NUNCA guardamos `payload.password`. Solo el hash.
            usuario = Usuario(
                username=payload.username,
                email=payload.email,
                hashed_password=hashed,
                rol=payload.rol,
                is_active=True,
            )

            # `add` del BaseRepository hace: session.add + flush + refresh.
            uow.usuarios.add(usuario)

            # --- 5. Devolver el DTO público ----------------------------------
            return UserPublic.model_validate(usuario)

    # =======================================================================
    # authenticate: login
    # =======================================================================
    def authenticate(self, username: str, password: str) -> Token:
        """
        Autentica un usuario y devuelve un JWT.

        Flujo:
          1. Buscar el usuario por username.
          2. Verificar que existe, está activo y la contraseña coincide.
          3. Emitir JWT firmado.

        Raises:
            AuthenticationError: si el usuario no existe, está inactivo
                                 o la contraseña no coincide (mismo
                                 mensaje para no filtrar info al atacante).
        """
        with UsuarioUnitOfWork(self._session) as uow:
            # --- 1. Buscar el usuario -----------------------------------------
            user = uow.usuarios.get_by_username(username)

            # --- 2. Verificar credenciales (genérico) -----------------------
            # Un solo `if` con OR: si falla cualquiera, mismo 401.
            # Esto evita que un atacante sepa si el username existe.
            if (
                user is None
                or not user.is_active
                or not verify_password(password, user.hashed_password)
            ):
                raise AuthenticationError("Credenciales inválidas.")

            # --- 3. Emitir el JWT --------------------------------------------
            # El `sub` (subject) del JWT es el username (estándar OAuth2).
            access_token = create_access_token(data={"sub": user.username})

            return Token(access_token=access_token, token_type="bearer")

    # =======================================================================
    # get_by_id: obtener un usuario por ID
    # =======================================================================
    def get_by_id(self, user_id: int) -> UserPublic:
        """
        Obtiene un usuario por su ID.

        Raises:
            ResourceNotFoundError: si no existe.
        """
        with UsuarioUnitOfWork(self._session) as uow:
            user = uow.usuarios.get_by_id(user_id)
            if user is None:
                raise ResourceNotFoundError(
                    resource="usuario",
                    identifier=str(user_id),
                )
            return UserPublic.model_validate(user)

    # =======================================================================
    # list_all: listar usuarios con paginación
    # =======================================================================
    def list_all(self, skip: int = 0, limit: int = 100) -> UserList:
        """
        Lista TODOS los usuarios (incluyendo desactivados) con paginación.
        Solo debería llamarse desde endpoints admin.
        """
        with UsuarioUnitOfWork(self._session) as uow:
            items = uow.usuarios.list_all(skip, limit)
            # Para el `total`, contamos los activos. Si quisiéramos contar
            # todos, agregaríamos un `count_all()` en el repository.
            total = uow.usuarios.count_active()
            return UserList(
                items=[UserPublic.model_validate(u) for u in items],
                total=total,
            )

    # =======================================================================
    # update: actualizar un usuario
    # =======================================================================
    def update(
        self,
        user_id: int,
        payload: UserUpdate,
        current_user: UserPublic,
    ) -> UserPublic:
        """
        Actualiza un usuario.

        Reglas:
          - Solo admin puede cambiar `is_active`.
          - Un admin no puede desactivarse a sí mismo.
          - Si cambia `password`, lo hasheamos.
        """
        with UsuarioUnitOfWork(self._session) as uow:
            user = uow.usuarios.get_by_id(user_id)
            if user is None:
                raise ResourceNotFoundError(
                    resource="usuario",
                    identifier=str(user_id),
                )

            # --- Regla: solo admin cambia is_active -------------------------
            if payload.is_active is not None and current_user.rol != "admin":
                raise AuthorizationError(
                    "Solo un administrador puede activar/desactivar usuarios."
                )

            # --- Anti self-lockout ------------------------------------------
            if (
                payload.is_active is False
                and current_user.rol == "admin"
                and current_user.id == user.id
            ):
                raise AuthorizationError(
                    "Un administrador no puede desactivarse a sí mismo."
                )

            # --- Aplicar cambios --------------------------------------------
            update_data = payload.model_dump(exclude_unset=True)

            # Si viene password en plaintext, lo hasheamos.
            if "password" in update_data:
                update_data["hashed_password"] = hash_password(
                    update_data.pop("password")
                )

            # Audit timestamp.
            update_data["updated_at"] = datetime.utcnow()

            # `model_copy(update=...)` aplica los cambios y devuelve NUEVA instancia.
            updated = user.model_copy(update=update_data)

            # Persistimos.
            updated = uow.usuarios.update(updated)
            return UserPublic.model_validate(updated)

    # =======================================================================
    # set_active: activar/desactivar un usuario (solo admin)
    # =======================================================================
    def set_active(
        self,
        user_id: int,
        is_active: bool,
        current_user: UserPublic,
    ) -> UserPublic:
        """
        Activa o desactiva un usuario. Atajo al estilo del modelo:
        POST /admin/usuarios/{id}/activar y POST /.../desactivar.
        """
        with UsuarioUnitOfWork(self._session) as uow:
            user = uow.usuarios.get_by_id(user_id)
            if user is None:
                raise ResourceNotFoundError(
                    resource="usuario",
                    identifier=str(user_id),
                )

            # Anti self-lockout para desactivación.
            if is_active is False and current_user.id == user.id:
                raise AuthorizationError(
                    "Un administrador no puede desactivarse a sí mismo."
                )

            updated = user.model_copy(
                update={"is_active": is_active, "updated_at": datetime.utcnow()}
            )
            updated = uow.usuarios.update(updated)
            return UserPublic.model_validate(updated)
