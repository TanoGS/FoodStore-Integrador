from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


def _none_if_blank(v: Optional[str]) -> Optional[str]:
    """Convierte cadenas vacías o solo espacios en None."""
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


class DireccionBase(BaseModel):
    # Opcionales: si no se mandan → null en BD
    alias:        Optional[str] = Field(default=None, max_length=50)
    piso:         Optional[str] = Field(default=None, max_length=10)
    departamento: Optional[str] = Field(default=None, max_length=10)

    # Requeridos: deben tener contenido real
    calle:         str = Field(..., min_length=2, max_length=100)
    numero:        str = Field(..., min_length=1, max_length=20)
    ciudad:        str = Field(..., min_length=2, max_length=100)
    codigo_postal: str = Field(..., min_length=3, max_length=20)
    predeterminada: bool = False

    @field_validator("alias", "piso", "departamento", mode="before")
    @classmethod
    def opcional_vacio_a_none(cls, v):
        return _none_if_blank(v)

    @field_validator("calle", "numero", "ciudad", "codigo_postal", mode="before")
    @classmethod
    def requerido_strip(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v


class DireccionCreate(DireccionBase):
    model_config = {
        "json_schema_extra": {
            "example": {
                "alias": "Casa",
                "calle": "Av. San Martín",
                "numero": "1234",
                "piso": "2",
                "departamento": "B",
                "ciudad": "Mendoza",
                "codigo_postal": "5500",
                "predeterminada": False,
            }
        }
    }


class DireccionUpdate(BaseModel):
    alias:         Optional[str]  = Field(default=None, max_length=50)
    calle:         Optional[str]  = Field(default=None, min_length=2, max_length=100)
    numero:        Optional[str]  = Field(default=None, min_length=1, max_length=20)
    piso:          Optional[str]  = None
    departamento:  Optional[str]  = None
    ciudad:        Optional[str]  = Field(default=None, min_length=2, max_length=100)
    codigo_postal: Optional[str]  = Field(default=None, min_length=3, max_length=20)
    predeterminada: Optional[bool] = None

    @field_validator("alias", "piso", "departamento", mode="before")
    @classmethod
    def opcional_vacio_a_none(cls, v):
        return _none_if_blank(v)

    @field_validator("calle", "numero", "ciudad", "codigo_postal", mode="before")
    @classmethod
    def requerido_strip(cls, v):
        if v is not None and isinstance(v, str):
            return v.strip()
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "alias": None,
                "calle": "Calle Las Heras",
                "numero": "500",
                "piso": None,
                "departamento": None,
                "ciudad": "Mendoza",
                "codigo_postal": "5500",
                "predeterminada": None,
            }
        }
    }


class DireccionPublic(DireccionBase):
    id:             int
    usuario_id:     int
    creado_en:      datetime
    actualizado_en: datetime
    eliminado_en:   Optional[datetime] = None

    class Config:
        from_attributes = True