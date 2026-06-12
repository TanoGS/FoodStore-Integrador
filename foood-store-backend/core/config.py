from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Food Store API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # Base de Datos
    DATABASE_URL: str

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    # ── Seguridad / JWT ──
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── MercadoPago ─────────────────────────────────────────────────────
    MP_ACCESS_TOKEN:    str = "TEST-DUMMY-TOKEN"
    MP_PUBLIC_KEY:      str = "TEST-DUMMY-PUBLIC-KEY"
    MP_NOTIFICATION_URL: str = "http://localhost:8000/api/v1/pagos/webhook"
    FRONTEND_URL:       str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()
