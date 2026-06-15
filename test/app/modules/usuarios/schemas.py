"""
Módulo: app/modules/usuarios/schemas.py
========================================

¿Qué hace este archivo?
------------------------
Define los **schemas de Pydantic** para el módulo Usuarios. Los schemas son
las "formas" de los datos que la API acepta (entrada) y devuelve (salida).

¿Por qué separar schemas de models?
------------------------------------
Porque tienen **responsabilidades distintas**:

  - **Model** (`models.py`): representa la TABLA. Sabe de columnas, índices,
    defaults a nivel DB. Se usa para persistir.

  - **Schema** (este archivo): representa el DTO (Data Transfer Object) que
    viaja por HTTP. Sabe de validaciones de entrada, formatos de salida, qué
    campos mostrar y cuáles ocultar (ej: `hashed_password` NUNCA sale al
    exterior).

Reglas de oro que aplicamos:
----------------------------
  1. **NUNCA devolver `hashed_password` en una respuesta**: el `UserPublic`
     ni siquiera lo tiene como atributo.
  2. **Schemas de entrada validan formato** (email, longitud mínima, regex).
  3. **Schemas de salida son read-only** (no aceptan valores para escribir).
  4. **Schemas de actualización son opcionales** (todos sus campos con
     `default=None`) para soportar PATCH parcial.

Patrón usado:
-------------
  - `UserCreate`: lo que el cliente envía para registrarse.
  - `UserLogin`: lo que envía para hacer login.
  - `UserPublic`: lo que devolvemos al cliente (NUNCA incluye el hash).
  - `UserUpdate`: lo que se puede modificar (todos opcionales).
  - `Token`: respuesta del endpoint /token.
  - `TokenPayload`: lo que guardamos DENTRO del JWT.
"""

# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
# `field_validator` y `EmailStr` son de Pydantic v2.
# `EmailStr` valida que el string tenga formato de email real.
# Si el email es inválido, Pydantic lanza ValidationError → 422.
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# `re` lo usamos para validar el username con una expresión regular:
# solo letras, números, guión bajo, guión medio. 3 a 50 caracteres.
import re

# Anotaciones de tipo modernas (Python 3.10+).
from typing import Literal

# `datetime` para los timestamps de auditoría de UserPublic.
from datetime import datetime


# ---------------------------------------------------------------------------
# CONSTANTE: roles permitidos
# ---------------------------------------------------------------------------
# Definimos los roles válidos como Literal type. Esto hace que Pydantic
# RECHACE cualquier valor que no esté en la lista, con un 422 claro.
RolLiteral = Literal["admin", "user"]


# ---------------------------------------------------------------------------
# REGEX: validación de username
# ---------------------------------------------------------------------------
# Solo letras, números, guión bajo (_) y guión medio (-). Sin espacios.
# Esto evita inyecciones de rutas tipo ".." o caracteres raros en URLs.
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,50}$")


# ===========================================================================
# SCHEMAS DE ENTRADA (lo que el cliente ENVÍA)
# ===========================================================================


class UserCreate(BaseModel):
    """
    Schema para **registrar un usuario nuevo**.

    Lo usa el endpoint `POST /usuarios/register`.

    Validaciones que aplica Pydantic automáticamente:
      - `username`: 3 a 50 caracteres, regex, único (la unicidad la valida
        el Service contra la DB, Pydantic no puede ver la DB).
      - `email`: formato de email real gracias a `EmailStr`.
      - `password`: mínimo 8 caracteres (defensa contra contraseñas triviales).
      - `rol`: debe ser "admin" o "user" (gracias a `RolLiteral`).
    """

    # `model_config` con `str_strip_whitespace=True` hace que si el cliente
    # manda " admin " con espacios, Pydantic los recorta automáticamente
    # antes de validar. Pequeño detalle, gran mejora de UX.
    model_config = ConfigDict(str_strip_whitespace=True)

    # --- username -------------------------------------------------------------
    # `min_length` y `max_length` los validamos con Pydantic ANTES del regex
    # para dar un error más específico ("too short" vs "invalid characters").
    username: str = Field(
        min_length=3,
        max_length=50,
        description="Nombre de usuario. 3-50 chars, letras/números/_/-.",
    )

    # --- email ----------------------------------------------------------------
    # `EmailStr` requiere tener `email-validator` instalado (ya está en
    # requirements). Valida formato real (algo@algo.tld).
    email: EmailStr = Field(
        description="Email válido. Se valida formato con Pydantic EmailStr.",
    )

    # --- password -------------------------------------------------------------
    # ⚠️ Este es el ÚNICO schema donde aceptamos `password` en plaintext.
    # El Service lo hashea con bcrypt ANTES de guardarlo en la DB.
    # En la respuesta NUNCA devolvemos este campo.
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Contraseña en plaintext. Mínimo 8 caracteres. "
        "Se hashea con bcrypt antes de persistir.",
    )

    # --- rol ------------------------------------------------------------------
    # Optional con default "user" para que un registro público no requiera
    # mandar el rol. Si alguien manda "superadmin" → 422 inmediato.
    rol: RolLiteral = Field(
        default="user",
        description='Rol del usuario. Solo "admin" o "user".',
    )

    # --- validador de username ------------------------------------------------
    # Pydantic v2 usa `field_validator` (no `validator` como en v1).
    # Se ejecuta DESPUÉS de las validaciones built-in (min/max length).
    @field_validator("username")
    @classmethod
    def validate_username_format(cls, v: str) -> str:
        """
        Valida que el username solo contenga caracteres permitidos.

        ¿Por qué un validador custom si Pydantic ya tiene min/max_length?
        Porque min/max_length validan longitud, pero no el CONTENIDO.
        Podrías tener "..." como username (3 chars pero inútil) o
        "mi usuario" con espacio (no se puede usar en URLs).
        """
        if not USERNAME_REGEX.match(v):
            # El mensaje de error llega al cliente como parte del 422.
            # Por eso es importante que sea claro y específico.
            raise ValueError(
                "El username solo puede contener letras, números, "
                "guión bajo (_) y guión medio (-). Sin espacios."
            )
        return v


class UserLogin(BaseModel):
    """
    Schema para **iniciar sesión**.

    Lo usa el endpoint `POST /usuarios/token` (form OAuth2 compatible).

    Diferencia con UserCreate:
      - NO valida el formato estricto del username (porque si el usuario
        tipeó mal, queremos que el endpoint responda 401 "credenciales
        inválidas", no 422 "formato inválido" — más seguro, no le damos
        pistas al atacante de si el username existe).
      - El password es obligatorio pero sin mínimo de longitud (idem:
        si lo manda vacío, que devuelva 401 genérico).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(
        min_length=1,
        max_length=50,
        description="Username. Sin validación de formato (401 genérico si falla).",
    )

    password: str = Field(
        min_length=1,
        max_length=128,
        description="Contraseña. Sin mínimo (401 genérico si falla).",
    )


class UserUpdate(BaseModel):
    """
    Schema para **actualizar un usuario** (PATCH).

    Lo usa el endpoint `PATCH /usuarios/{id}`.

    Reglas:
      - TODOS los campos son opcionales (default=None) para soportar
        actualizaciones parciales. Si el cliente solo quiere cambiar el
        email, manda solo `{"email": "nuevo@..."}`.
      - NO permite cambiar `username` ni `rol` (decisión de seguridad: el
        username es identificador de login, cambiarlo rompe auditoría; el
        rol se cambia por un endpoint específico de admin).
    """

    # `model_config` con `extra="forbid"` rechaza campos no declarados.
    # Si el cliente manda `{"password": "...", "campo_raro": "x"}`,
    # Pydantic devuelve 422 con "campo_raro no permitido".
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr | None = Field(
        default=None,
        description="Nuevo email. Si se omite, no se modifica.",
    )

    # ⚠️ Misma lógica que en `UserCreate`: este es el ÚNICO schema donde
    # aceptamos `password` en plaintext. El Service lo hashea.
    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="Nueva contraseña. Si se omite, no se modifica.",
    )

    is_active: bool | None = Field(
        default=None,
        description="Activar/desactivar usuario. Solo admins.",
    )


# ===========================================================================
# SCHEMAS DE SALIDA (lo que la API DEVUELVE al cliente)
# ===========================================================================


class UserPublic(BaseModel):
    """
    Schema de **salida pública** de un usuario.

    Lo que devolvemos al cliente. Por seguridad:
      - NUNCA incluye `hashed_password`.
      - `id`, `username`, `email`, `rol`, `is_active` son read-only.

    `from_attributes=True` permite construirlo directamente desde un
    objeto SQLModel: `UserPublic.model_validate(usuario_db)`. Antes en
    Pydantic v1 era `orm_mode=True`.
    """

    # `from_attributes=True` es CLAVE para devolver entidades de la DB
    # sin tener que copiar campo por campo. Le dice a Pydantic: "podés
    # leer atributos de un objeto cualquiera (como un Model de SQLAlchemy)".
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    rol: RolLiteral
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserList(BaseModel):
    """
    Schema de salida para **listar usuarios** (respuesta paginada).

    Lo usa el endpoint `GET /usuarios/` (admin only).

    ¿Por qué envolver la lista en un objeto en vez de devolver un array?
    ---------------------------------------------------------------------
    Por **extensibilidad**. Si hoy devolvemos `[{...}, {...}]`, mañana
    queremos agregar `total`, `page`, `per_page` y romperíamos la API.
    Con `{"items": [...], "total": 42}` podemos crecer sin breaking changes.
    """

    items: list[UserPublic] = Field(
        description="Lista de usuarios en la página actual.",
    )
    total: int = Field(
        ge=0,
        description="Cantidad TOTAL de usuarios (no solo de esta página).",
    )


# ===========================================================================
# SCHEMAS DE AUTENTICACIÓN (Token)
# ===========================================================================


class Token(BaseModel):
    """
    Schema de respuesta del endpoint `POST /usuarios/token`.

    OAuth2 estándar: devuelve `access_token` y `token_type="bearer"`.
    El frontend guarda el access_token y lo manda en cada request
    (vía cookie HttpOnly en nuestro caso, o Authorization header).
    """

    access_token: str = Field(
        description="JWT firmado. Se envía en cookie HttpOnly en cada request.",
    )
    token_type: str = Field(
        default="bearer",
        description='Tipo de token. Estándar OAuth2: "bearer".',
    )


class TokenPayload(BaseModel):
    """
    Schema del **payload DECODIFICADO** del JWT.

    NO es lo que se manda al cliente, sino lo que está DENTRO del token
    una vez que lo verificamos con `jwt.decode()`. Lo usamos para extraer
    el `sub` (username) y validar el `type` (debe ser "access", no "refresh"
    ni otra cosa).
    """

    sub: str | None = Field(
        default=None,
        description='Subject. Contiene el username del usuario.',
    )
    type: str | None = Field(
        default=None,
        description='Tipo de token. Validamos que sea "access".',
    )
    exp: int | None = Field(
        default=None,
        description="Timestamp de expiración (epoch).",
    )
    iat: int | None = Field(
        default=None,
        description="Timestamp de emisión (epoch).",
    )
