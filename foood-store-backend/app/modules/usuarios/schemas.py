from pydantic import BaseModel, EmailStr
from typing import Optional

class UsuarioCreate(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    password: str # En la Fase 6 lo llamaremos password plano y lo hashearemos
    telefono: Optional[str] = None

class UsuarioResponse(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str
    rol_nombre: str
    activo: bool

class LoginRequest(BaseModel):
    email: EmailStr
    password: str