from typing import Optional, List
from sqlmodel import SQLModel, Field
from datetime import datetime


# ── Entrada ─────────────────────────────────────────────────────────────────────────────

class ProductoCreate(SQLModel):
    """Body para POST /productos/"""
    nombre: str = Field(max_length=100)
    descripcion: Optional[str] = None
    precio_base: float = Field(ge=0)
    es_personalizable: bool = False
    imagen_url: Optional[str] = None
    stock_disponible: int = Field(default=0, ge=0)
    activo: bool = True
    categoria_ids: List[int] = Field(default=[])


class ProductoUpdate(SQLModel):
    """Body para PATCH /productos/{id} — todos los campos opcionales."""
    nombre: Optional[str] = Field(default=None, max_length=100)
    descripcion: Optional[str] = None
    precio_base: Optional[float] = Field(default=None, ge=0)
    es_personalizable: Optional[bool] = None
    imagen_url: Optional[str] = None
    stock_disponible: Optional[int] = Field(default=None, ge=0)
    activo: Optional[bool] = None
    categoria_ids: Optional[List[int]] = None


# ── Salida ─────────────────────────────────────────────────────────────────────────────

class ProductoPublic(SQLModel):
    """Response model: campos que se exponen al cliente."""
    id: int
    nombre: str
    descripcion: Optional[str] = None
    precio_base: float
    es_personalizable: bool
    imagen_url: Optional[str] = None
    stock_disponible: int
    activo: bool
    eliminado_en: Optional[datetime] = None


class ProductoList(SQLModel):
    """Response model paginado para GET /productos/"""
    data: List[ProductoPublic]
    total: int