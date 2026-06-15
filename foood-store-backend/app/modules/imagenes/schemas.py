from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class SincronizarRequest(BaseModel):
    """Body para el endpoint de sincronización con Cloudinary."""
    folder: str = "productos"


class ImagenPublic(BaseModel):
    id: int
    public_id: str
    url: str
    secure_url: Optional[str]
    formato: str
    ancho: int
    alto: int
    bytes: int
    folder: str
    recurso_tipo: str
    nombre_archivo: Optional[str]
    creado_en: datetime

    class Config:
        from_attributes = True


class ImagenList(BaseModel):
    data: List[ImagenPublic]
    total: int
