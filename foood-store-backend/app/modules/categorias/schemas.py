from pydantic import BaseModel
from typing import Optional

class CategoriaCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    padre_id: Optional[int] = None

class CategoriaResponse(CategoriaCreate):
    id: int