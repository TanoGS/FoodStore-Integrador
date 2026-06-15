# =============================================================================
# config.py — Configuración centralizada de la aplicación
# =============================================================================
#
# CONCEPTO CLAVE: Settings vs Variables de entorno
# ----------------------------------------------------
# pydantic-settings lee variables de entorno (o de un archivo .env) y las
# valida según los tipos declarados. Esto nos da:
#   1. Type safety: si una variable esperada no existe o tiene tipo incorrecto,
#      la app FALLA RÁPIDO al arrancar (no en runtime a mitad de un request).
#   2. Documentación implícita: la clase ES el contrato de configuración.
#   3. Autocompletado en IDEs.
#
# CONVENCIÓN: UPPERCASE para todo
# ----------------------------------------------------
# Los nombres de atributos en Python son UPPERCASE (igual que las env vars)
# para que el código sea simétrico: settings.APP_NAME == $APP_NAME.
# pydantic-settings matchea env vars case-insensitive, así que no hay drama.
# =============================================================================

from typing import Literal
from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración de la aplicación leída desde variables de entorno.

    Convenciones:
      - Campos obligatorios SIN valor por defecto → la app no arranca sin ellos.
      - Campos OPCIONALES con default → la app funciona sin configurarlos.
      - UPPERCASE en todo para simetría con las env vars.
    """

    # ─── Identidad de la app ─────────────────────────────────────────────────
    APP_NAME: str = "API Middlewares Testing"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "production", "test"] = "development"

    # ─── Base de datos PostgreSQL ────────────────────────────────────────────
    # Variables sueltas que se combinan en DATABASE_URL más abajo.
    # Defaults razonables para desarrollo local.
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "api_testing"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # Alternativamente, se puede pasar DATABASE_URL completa (toma precedence).
    # Útil en producción donde el orquestador ya la construye.
    DATABASE_URL_OVERRIDE: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """
        Construye la URL de conexión a PostgreSQL.

        Si se pasó DATABASE_URL_OVERRIDE explícitamente, gana. Si no, se
        compone a partir de las variables sueltas.
        """
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # URL específica para tests (SQLite in-memory por default).
    TEST_DATABASE_URL: str = "sqlite:///:memory:"

    # ─── JWT (autenticación) ─────────────────────────────────────────────────
    # SECRET_KEY: clave para firmar los tokens. OBLIGATORIA.
    # En producción debe venir de un secret manager (Vault, AWS Secrets Manager).
    SECRET_KEY: str
    # Algoritmo de firma. HS256 (HMAC-SHA256) es suficiente para apps single-issuer.
    ALGORITHM: str = "HS256"
    # Tiempo de vida del access token. 60 min es un balance razonable.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ─── Admin inicial (seed) ────────────────────────────────────────────────
    # Credenciales del usuario admin que crea el seed al arrancar.
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "admin123"

    # ─── Logging ─────────────────────────────────────────────────────────────
    # Nivel de log. Literal evita typos (typo en el .env → falla validación).
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ─── Rate Limiting ───────────────────────────────────────────────────────
    # Límite por defecto: peticiones por minuto por cliente identificado.
    RATE_LIMIT_DEFAULT_PER_MINUTE: int = 60
    RATE_LIMIT_DEFAULT_BURST: int = 10
    # Límite estricto para endpoints de autenticación (mitiga fuerza bruta).
    RATE_LIMIT_AUTH_PER_MINUTE: int = 5
    RATE_LIMIT_AUTH_BURST: int = 3

    # ─── Middlewares / Performance ───────────────────────────────────────────
    # Umbral para considerar un request como "lento" (log de warning).
    SLOW_REQUEST_THRESHOLD_MS: int = 500

    # ─── CORS ────────────────────────────────────────────────────────────────
    # Orígenes permitidos para el frontend. Lista separada por comas en .env.
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @field_validator("CORS_ALLOWED_ORIGINS")
    @classmethod
    def parse_cors_origins(cls, v: str) -> list[str]:
        """
        Convierte el string separado por comas del .env en una lista.

        .env → "http://a.com,http://b.com"  →  ["http://a.com", "http://b.com"]
        """
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def CORS_ORIGINS(self) -> list[str]:
        """Alias para `CORS_ALLOWED_ORIGINS` parseado (lista)."""
        v = self.CORS_ALLOWED_ORIGINS
        if isinstance(v, list):
            return v
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rate_limit_default_burst(self) -> int:
        """Alias lowercase para uso en middleware."""
        return self.RATE_LIMIT_DEFAULT_BURST

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rate_limit_default_per_minute(self) -> int:
        """Alias lowercase para uso en middleware."""
        return self.RATE_LIMIT_DEFAULT_PER_MINUTE

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rate_limit_auth_burst(self) -> int:
        """Alias lowercase para uso en middleware."""
        return self.RATE_LIMIT_AUTH_BURST

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rate_limit_auth_per_minute(self) -> int:
        """Alias lowercase para uso en middleware."""
        return self.RATE_LIMIT_AUTH_PER_MINUTE

    # ─── Config del modelo pydantic-settings ─────────────────────────────────
    # Define de dónde leer las variables y cómo comportarse con extras.
    model_config = SettingsConfigDict(
        # Archivo .env a leer (en la raíz del proyecto).
        env_file=".env",
        env_file_encoding="utf-8",
        # case_sensitive=False: acepta SECRET_KEY o secret_key (mayús o minús).
        case_sensitive=False,
        # extra="ignore": si hay variables de más en .env, las ignora.
        extra="ignore",
    )


# Instancia global — importar en cualquier archivo como:
#     from app.core.config import settings
# Esto lee .env UNA sola vez al importarse (singleton).
settings = Settings()
