from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
import enum

class RolUsuario(str, enum.Enum):
    CLIENTE = "CLIENTE"
    ADMIN = "ADMIN"
    GESTOR_STOCK = "GESTOR_STOCK"
    GESTOR_PEDIDOS = "GESTOR_PEDIDOS"

class Usuario(SQLModel, table=True):
    __tablename__ = "usuario"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    password: str = Field(max_length=255) # TEMPORAL
    nombre: str = Field(max_length=100)
    apellido: str = Field(max_length=100)
    rol: RolUsuario = Field(default=RolUsuario.CLIENTE)
    activo: bool = Field(default=True)
    
    creado_en: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    eliminado_en: Optional[datetime] = Field(default=None)