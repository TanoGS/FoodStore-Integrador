from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone

class Rol(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(unique=True, index=True) # Ej: "ADMIN", "CLIENTE"
    descripcion: Optional[str] = None

class Usuario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str # Aquí luego guardaremos la contraseña encriptada con bcrypt
    nombre: str
    apellido: str
    telefono: Optional[str] = None
    activo: bool = Field(default=True)
    
    # Manejo de fechas de creación
    creado_en: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Clave foránea al Rol
    rol_id: Optional[int] = Field(default=None, foreign_key="rol.id")