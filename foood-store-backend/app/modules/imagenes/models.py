from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger, DateTime
from datetime import datetime, timezone


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Imagen(SQLModel, table=True):
    __tablename__ = "imagenes"

    id: Optional[int] = Field(default=None, primary_key=True, sa_type=BigInteger)

    # Cloudinary
    public_id: str = Field(unique=True, index=True, max_length=255)
    url: str = Field(max_length=500)
    secure_url: Optional[str] = Field(default=None, max_length=500)
    formato: str = Field(max_length=10)  # jpg, png, webp
    ancho: int = Field(default=0)
    alto: int = Field(default=0)
    bytes: int = Field(default=0)
    folder: str = Field(default="productos", max_length=255)
    recurso_tipo: str = Field(default="image", max_length=20)

    # Metadata
    subido_por_id: int = Field(foreign_key="usuarios.id", sa_type=BigInteger)
    nombre_archivo: Optional[str] = Field(default=None, max_length=255)

    # Timestamps
    creado_en: datetime = Field(default_factory=_utc_now, sa_type=DateTime(timezone=True))
    eliminado_en: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True), nullable=True)
