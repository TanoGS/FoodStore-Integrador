from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import BigInteger, DateTime # Importamos los tipos nativos de SQLAlchemy
from typing import List, Optional
from datetime import datetime
import app
# ==============================================================================
# 1. TABLA INTERMEDIA: usuarios_roles
# ==============================================================================
class UsuarioRol(SQLModel, table=True):
    __tablename__ = "usuarios_roles"
    
    usuario_id: int = Field(
        default=None, 
        foreign_key="usuarios.id", 
        primary_key=True,
        sa_type=BigInteger  
    )
    rol_codigo: str = Field(
        default=None, 
        foreign_key="roles.codigo", 
        primary_key=True,
        max_length=20
    )
    
    asignado_por_id: Optional[int] = Field(
        default=None, 
        foreign_key="usuarios.id",
        sa_type=BigInteger,  
        nullable=True
    )
    #  Usamos DateTime con soporte de zona horaria
    expires_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))

    usuario: "Usuario" = Relationship(
        back_populates="roles_enlaces",
        sa_relationship_kwargs={"foreign_keys": "[UsuarioRol.usuario_id]"}
    )
    asignador: Optional["Usuario"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[UsuarioRol.asignado_por_id]"}
    )
    rol: "Rol" = Relationship(back_populates="usuarios_enlaces")


# ==============================================================================
# 2. TABLA INTERMEDIA: roles_permisos
# ==============================================================================
class RolPermiso(SQLModel, table=True):
    __tablename__ = "roles_permisos"
    
    rol_codigo: str = Field(default=None, foreign_key="roles.codigo", primary_key=True, max_length=20)
    permiso_id: int = Field(default=None, foreign_key="permisos.id", primary_key=True)


# ==============================================================================
# 3. TABLA: permisos
# ==============================================================================
class Permiso(SQLModel, table=True):
    __tablename__ = "permisos"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(unique=True, index=True, max_length=50)
    descripcion: Optional[str] = Field(default=None, max_length=255)
    
    roles: List["Rol"] = Relationship(back_populates="permisos", link_model=RolPermiso)


# ==============================================================================
# 4. TABLA: roles
# ==============================================================================
class Rol(SQLModel, table=True):
    __tablename__ = "roles"
    
    codigo: str = Field(primary_key=True, max_length=20)
    nombre: str = Field(unique=True, index=True, max_length=50)
    descripcion: Optional[str] = Field(default=None, max_length=255)
    
    usuarios_enlaces: List[UsuarioRol] = Relationship(back_populates="rol")
    permisos: List[Permiso] = Relationship(back_populates="roles", link_model=RolPermiso)


# ==============================================================================
# 5. TABLA: usuarios
# ==============================================================================
class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"
    
   
    id: Optional[int] = Field(default=None, primary_key=True, sa_type=BigInteger)
    email: str = Field(unique=True, index=True, max_length=100)
    password: str = Field(max_length=255)
    nombre: str = Field(max_length=50)
    apellido: str = Field(max_length=50)
    cel: Optional[str] = Field(default=None, max_length=20)
    activo: bool = Field(default=True)
    
    creado_en: datetime = Field(default_factory=datetime.utcnow)
    actualizado_en: Optional[datetime] = Field(default=None)
    eliminado_en: Optional[datetime] = Field(default=None)
    
    roles_enlaces: List[UsuarioRol] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={"foreign_keys": "[UsuarioRol.usuario_id]", "cascade": "all, delete-orphan"}
    )
