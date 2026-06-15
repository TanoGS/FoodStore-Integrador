"""
Módulo: app/modules/usuarios/models.py
========================================

¿Qué hace este archivo?
------------------------
Define la **capa de persistencia** del módulo de Usuarios. Es decir, cómo se
traduce una entidad de dominio "Usuario" a una **tabla real de base de datos**.

¿Por qué existe esta capa separada?
------------------------------------
En arquitectura limpia / hexagonal, separamos:

    Router  →  Service  →  UnitOfWork  →  Repository  →  Model (DB)
    (HTTP)    (lógica)    (transacción)   (consultas)     (datos)

El `Model` (esta capa) SOLO sabe de columnas y tipos SQL. No sabe nada de
HTTP, ni de validaciones de entrada (eso es el Schema), ni de reglas de
negocio (eso es el Service).

¿Qué tecnología usamos?
-----------------------
**SQLModel** (de los creadores de FastAPI y Pydantic). Es un ORM que combina
Pydantic + SQLAlchemy en una sola clase. Por eso cada atributo del modelo
tiene doble propósito:

  - Para SQLAlchemy: definir la columna de la tabla (tipos, constraints, FKs).
  - Para Pagedantic: validar y serializar datos (types, defaults, validators).

Decisión pedagógica:
--------------------
  - Marcamos `table=True` para indicarle a SQLModel "esta clase ES una tabla".
  - El `id` lo definimos `Optional[int] = Field(default=None, primary_key=True)`
    para que SQLAlchemy lo trate como autoincremental manejado por la DB.
  - El `rol` lo modelamos como `str` (no Enum) para simplificar tests y
    migraciones. La validación semántica se hace en el Schema con Literal.
"""

# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
# `datetime` se usa para timestamps de auditoría (created_at, updated_at).
from datetime import datetime

# `Field` es la API de SQLModel/Pydantic para declarar columnas con metadata
# (primary_key, index, default, foreign_key, etc.).
from sqlmodel import Field, SQLModel


# ---------------------------------------------------------------------------
# CLASE: Usuario (tabla real de la base de datos)
# ---------------------------------------------------------------------------
class Usuario(SQLModel, table=True):
    """
    Modelo de persistencia de un Usuario del sistema.

    Esta clase representa la **tabla `usuario`** en PostgreSQL/SQLite.
    Cada atributo de clase corresponde a una columna.

    Convenciones aplicadas:
    -----------------------
    1. `id` opcional con default None: SQLAlchemy lo maneja como autoincrement.
    2. Campos únicos (username, email): `unique=True` crea un índice único en DB.
    3. `hashed_password` (no `password`): principio de nunca almacenar el
       plaintext. Aunque el ORM no lo obliga, el nombre lo comunica.
    4. `rol` como string simple: para que migraciones de schema no se rompan
       cuando agreguemos roles. Se valida a nivel Schema/Service.
    5. `is_active` como `bool` con default True: el "soft delete" del sistema.
       Nunca borramos un usuario físicamente, solo lo desactivamos.
    6. `created_at` / `updated_at`: auditoría. `updated_at` se setea en el
       Repository con `datetime.utcnow()` antes de un UPDATE.
    """

    # --- Identificador ---------------------------------------------------------
    # `Optional[int]` con `default=None` es el patrón canónico de SQLModel para
    # columnas autoincrementales: la DB genera el valor al hacer INSERT.
    # `primary_key=True` crea la PK de la tabla.
    id: int | None = Field(default=None, primary_key=True, index=True)

    # --- Credenciales / identificación ----------------------------------------
    # `unique=True` agrega constraint UNIQUE en la DB (defensa en profundidad:
    # incluso si alguien escribe directo a la tabla sin pasar por el Service,
    # la DB rechaza duplicados). `index=True` acelera búsquedas por username.
    # `max_length` evita ataques de denegación por strings gigantes.
    username: str = Field(
        unique=True,
        index=True,
        max_length=50,
        min_length=3,
        description="Nombre de usuario único. Solo letras, números y guión bajo.",
    )

    # Email único. La validación de FORMATO (que tenga @, etc.) se hace en el
    # Schema con `EmailStr` de Pydantic; acá solo declaramos la columna.
    email: str = Field(
        unique=True,
        index=True,
        max_length=255,
        description="Email único. Se valida formato a nivel Schema.",
    )

    # --- Seguridad ------------------------------------------------------------
    # ⚠️ NUNCA jamás de los jamases guardamos la contraseña en texto plano.
    # El campo guarda el HASH generado por bcrypt (en `core/security.py`).
    # El nombre mismo lo deja explícito: `hashed_password`.
    # `nullable=False` (default en SQLModel cuando no tiene default=None).
    hashed_password: str = Field(
        max_length=255,
        description="Hash bcrypt de la contraseña. NUNCA plaintext.",
    )

    # --- Autorización (RBAC) --------------------------------------------------
    # Roles disponibles: "admin", "user" (convención simple).
    # Lo modelamos como `str` en vez de `Enum` para:
    #   - evitar migraciones cada vez que agreguemos un rol,
    #   - que el JSON se serialice como string directamente,
    #   - que SQLAlchemy no cree un CHECK constraint que rompa tests con SQLite.
    # La validación de "este string es un rol válido" se hace en el Schema
    # usando `Literal["admin", "user"]` o un Enum de Pydantic.
    rol: str = Field(
        default="user",
        max_length=20,
        description='Rol RBAC. Valores esperados: "admin" o "user".',
    )

    # --- Estado ---------------------------------------------------------------
    # Soft delete: si `is_active=False`, el usuario no puede loguearse
    # (ver `deps.get_current_active_user`). Nunca hacemos DELETE físico.
    is_active: bool = Field(
        default=True,
        description="False = usuario desactivado. Soft delete, no se borra de DB.",
    )

    # --- Auditoría ------------------------------------------------------------
    # Timestamps de creación/actualización. UTC siempre (nunca local time).
    # `sa_column_kwargs` permite pasar kwargs extra al Column de SQLAlchemy
    # en caso de necesitar features específicas del motor (ej: server_default
    # en Postgres para que la DB ponga el timestamp por su cuenta).
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Fecha de creación del registro (UTC).",
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Fecha de última actualización (UTC). Lo actualiza el Repository.",
    )

    # --- Representación -------------------------------------------------------
    # Esto es solo para debugging y logs: cuando hacemos `print(usuario)` o
    # el logger lo serializa, vemos algo legible en vez de `<Usuario object>`.
    def __repr__(self) -> str:
        return (
            f"Usuario(id={self.id}, username='{self.username}', "
            f"rol='{self.rol}', is_active={self.is_active})"
        )
