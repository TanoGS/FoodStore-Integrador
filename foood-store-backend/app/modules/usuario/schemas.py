from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import List, Optional
from datetime import datetime

# ==============================================================================
# 1. ESQUEMA: RolPublic (Molde para exponer la Clave Natural)
# ==============================================================================
class RolPublic(BaseModel):
    codigo: str  # Ej: "ADMIN", "GESTOR_STOCK"
    nombre: str  # Ej: "Administrador General"
    descripcion: Optional[str] = None

    class Config:
        from_attributes = True


# ==============================================================================
# 2. ESQUEMAS: Usuario (Estructura de Datos e Inputs)
# ==============================================================================
class UsuarioBase(BaseModel):
    email: EmailStr
    nombre: str
    apellido: str
    cel: Optional[str] = None  


class UsuarioCreate(UsuarioBase):
    password: str
    # Cambiamos IDs numéricos por la Clave Natural de tipo texto (Códigos)
    role_codigos: Optional[List[str]] = None  # Ej: ["GESTOR_STOCK"]


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    cel: Optional[str] = None  
    activo: Optional[bool] = None


class UsuarioPublic(UsuarioBase):
    id: int
    activo: bool
    creado_en: datetime
    actualizado_en: Optional[datetime] = None
    eliminado_en: Optional[datetime] = None
    roles: List[RolPublic] = []

    class Config:
        from_attributes = True

    #  EL INTERCEPTOR (Model Validator) 
    @model_validator(mode="before")
    @classmethod
    def aplanar_roles_enlaces(cls, data):
        """
        Como la relación Muchos a Muchos ahora es explícita mediante 'roles_enlaces',
        al hacer UsuarioPublic.model_validate(usuario_orm), este validador entra en juego
        antes de serializar, extrae los objetos de la tabla Rol y los inserta limpios
        en el arreglo 'roles' para que el frontend los consuma de forma transparente.
        """
        if hasattr(data, "roles_enlaces"):
            # Extraemos la entidad máter 'rol' desde cada elemento de la tabla asociativa
            roles_reales = [enlace.rol for enlace in data.roles_enlaces if enlace.rol]
            
            # Re-empaquetamos la información como un diccionario compatible con Pydantic
            return {
                "id": data.id,
                "email": data.email,
                "nombre": data.nombre,
                "apellido": data.apellido,
                "cel": data.cel,
                "activo": data.activo,
                "creado_en": data.creado_en,
                "actualizado_en": data.actualizado_en,
                "eliminado_en": data.eliminado_en,
                "roles": roles_reales
            }
        return data


# ==============================================================================
# 3. ESQUEMAS: Respuestas de Colecciones
# ==============================================================================
class UsuarioList(BaseModel):
    data: List[UsuarioPublic]
    total: int


class AsignarRolesInput(BaseModel):
    role_codigos: List[str] = Field(..., min_length=1, description="Códigos de roles a asignar (reemplaza los actuales)")