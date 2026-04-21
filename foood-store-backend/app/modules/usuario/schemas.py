from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from .models import RolUsuario

class UsuarioBase(BaseModel):
    email: EmailStr
    nombre: str = Field(..., max_length=100)
    apellido: str = Field(..., max_length=100)
    rol: RolUsuario = RolUsuario.CLIENTE

class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=2)

class UsuarioResponse(UsuarioBase):
    id: int
    activo: bool
    creado_en: datetime
    eliminado_en: Optional[datetime] = None

    class Config:
        from_attributes = True

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    rol: Optional[RolUsuario] = None
    activo: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=2)