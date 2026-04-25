from typing import Optional, List
from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from datetime import datetime

from app.modules.producto.schemas import ProductoPublic


# ── Entrada ─────────────────────────────────────────────────────────────────────────────

class CategoriaCreate(SQLModel):
    """Body para POST /categorias/"""
    nombre: str = Field(max_length=100)
    descripcion: Optional[str] = Field(default=None, max_length=255)
    padre_id: Optional[int] = None


class CategoriaUpdate(SQLModel):
    """Body para PATCH /categorias/{id} — todos los campos opcionales."""
    nombre: Optional[str] = Field(default=None, max_length=100)
    descripcion: Optional[str] = Field(default=None, max_length=255)
    padre_id: Optional[int] = None


# ── Salida ─────────────────────────────────────────────────────────────────────────────

class CategoriaPublic(SQLModel):
    """Response model: campos que se exponen al cliente."""
    id: int
    nombre: str
    descripcion: Optional[str] = None
    padre_id: Optional[int] = None
    eliminado_en: Optional[datetime] = None


class CategoriaList(SQLModel):
    """Response model paginado para GET /categorias/"""
    data: List[CategoriaPublic]
    total: int


# ── Cross-module ───────────────────────────────────────────────────────────────────────────

class CategoriaWithProductos(BaseModel):
    """
    Response model para GET /categorias/{id}/productos y
    GET /categorias/con-productos.
    Usa BaseModel puro para evitar conflictos del validador de SQLModel
    al anidar instancias Pydantic en la construcción del dict.
    """
    id: int
    nombre: str
    descripcion: Optional[str] = None
    padre_id: Optional[int] = None
    eliminado_en: Optional[datetime] = None
    productos: List[ProductoPublic] = []

    model_config = {"from_attributes": True}


class CategoriaConProductosList(SQLModel):
    """Response model para GET /categorias/con-productos"""
    data: List[CategoriaWithProductos]
    total: int