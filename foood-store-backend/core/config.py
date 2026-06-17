import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Food Store API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

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
    MP_NOTIFICATION_URL: str = "http://localhost:8000/api/v1/pagos/webhook"    # Secret para validar la firma de los webhooks IPN (configurar en el panel MP).
    # Si está en blanco, la validación se saltea (desarrollo local).
    MP_WEBHOOK_SECRET:  str = ""
    FRONTEND_URL:       str = "http://localhost:5173"

    # ── Cloudinary ──────────────────────────────────────────────────────
    CLOUDINARY_CLOUD_NAME:  str
    CLOUDINARY_API_KEY:     str = "495238629622477"
    CLOUDINARY_API_SECRET:  str
    CLOUDINARY_FOLDER:      str = "foodstore"
    CLOUDINARY_MAX_FILE_MB: int = 5

    class Config:
        # Buscar .env en la carpeta del proyecto (backend)
        env_file = os.path.join(os.path.dirname(__file__), "..", ".env")


settings = Settings()
