# =============================================================================
# security.py — Utilidades de seguridad (JWT + hashing de contraseñas)
# =============================================================================
#
# CONCEPTO CLAVE: JWT (JSON Web Token)
# ----------------------------------------------------
# Un JWT es un string con tres partes separadas por puntos:
#   header.payload.signature
#
#   - header:      algoritmo usado (ej: HS256) y tipo ("JWT").
#   - payload:     los "claims" (datos). Van en BASE64, NO encriptados.
#                  Cualquiera puede leerlos. La seguridad está en la FIRMA.
#   - signature:   HMAC-SHA256(header + payload, SECRET_KEY). Si alguien
#                  modifica el payload, la firma deja de coincidir.
#
# ESTÁNDAR DE CLAIMS (registrados en RFC 7519):
#   - sub:    subject (identificador del usuario, ej: username)
#   - exp:    expiration time (segundos desde epoch)
#   - iat:    issued at (cuándo se emitió)
#   - type:   tipo de token ("access" vs "refresh")
#
# ¿POR QUÉ passlib EN VEZ DE bcrypt DIRECTO?
# ----------------------------------------------------
# passlib es una abstracción. Si mañana queremos migrar a Argon2 (más moderno
# que bcrypt), solo cambiamos `schemes=["bcrypt"]` → `schemes=["argon2"]`
# y todos los hashes viejos siguen verificándose (gracias a deprecated="auto").
# =============================================================================

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# ─── Hashing de contraseñas (bcrypt) ─────────────────────────────────────────

# CryptContext: abstracción sobre algoritmos de hashing.
# - schemes=["bcrypt"]: usa bcrypt como algoritmo principal.
# - deprecated="auto": cuando se verifique un hash con un algoritmo "deprecated",
#   passlib lo reemplaza automáticamente por el actual (re-hash transparente).
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """
    Hashea una contraseña en texto plano usando bcrypt.

    bcrypt INCLUYE un salt aleatorio en cada hash, así que dos llamadas
    con la misma contraseña producen hashes distintos. Esto es deseable:
    impide ataques con rainbow tables (tablas precomputadas de hashes).

    Costo: bcrypt es intencionalmente LENTO (~100ms por hash). Esto
    hace que un ataque de fuerza bruta sea computacionalmente costoso.
    """
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con un hash bcrypt.

    passlib se encarga de:
      1. Extraer el salt del hash almacenado.
      2. Hashear `plain` con ese mismo salt.
      3. Comparar en TIEMPO CONSTANTE (mitiga timing attacks).

    Devuelve True si coinciden, False en caso contrario.
    """
    return pwd_context.verify(plain, hashed)


# ─── JWT (JSON Web Tokens) ───────────────────────────────────────────────────

def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Genera un JWT firmado con HS256.

    Args:
        data: payload base. Convención: incluir {"sub": username, "role": role}.
        expires_delta: tiempo de vida custom. Si es None, usa el de settings.

    Returns:
        String con el JWT firmado (header.payload.signature).

    Notas de seguridad:
      - Usamos timezone.utc para evitar ambigüedades (timestamp debe ser absoluto).
      - El claim "type" distingue access tokens de refresh tokens, evitando
        que un atacante use un refresh token como access token.
    """
    # Copia defensiva: no mutamos el dict del caller.
    to_encode = data.copy()

    # Calcula la expiración.
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Agrega claims estándar (registered claims del RFC 7519).
    to_encode.update({
        "type": "access",   # Para distinguirlo de refresh tokens.
        "exp": expire,      # Expiración (estándar JWT).
        "iat": datetime.now(timezone.utc),  # "Issued At" (cuándo se creó).
    })

    # Firma con la SECRET_KEY usando el algoritmo configurado.
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """
    Decodifica y valida un JWT.

    Devuelve el payload (dict) si es válido, None si:
      - La firma no coincide (token manipulado).
      - El token está expirado (claim exp).
      - El algoritmo no es el esperado.
      - El tipo no es "access" (defensa contra reuso de refresh tokens).

    NOTA: Devolvemos None en vez de raise. Esto permite que la dependencia
    get_current_user decida si devolver 401 o seguir como anónimo.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        # Validación adicional: tipo de token.
        # Defensa contra reuso: si alguien roba un refresh token, no puede
        # usarlo como access token (asumiendo que los refresh se distinguen).
        if payload.get("type") != "access":
            return None

        return payload

    except JWTError:
        # Cualquier error de jose (firma, expiración, formato) → token inválido.
        return None
