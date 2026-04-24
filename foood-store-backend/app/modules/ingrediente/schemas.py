from typing import Optional, List
from sqlmodel import SQLModel, Field
from datetime import datetime


# ── Entrada ─────────────────────────────────────────────────────────────────────────────

class IngredienteCreate(SQLModel):
    """Body para POST /ingredientes/"""
    nombre: str = Field(max_length=100)
    es_alergeno: bool = False


class IngredienteUpdate(SQLModel):
    """Body para PATCH /ingredientes/{id} — todos los campos opcionales."""
    nombre: Optional[str] = Field(default=None, max_length=100)
    es_alergeno: Optional[bool] = None


# ── Salida ─────────────────────────────────────────────────────────────────────────────

class IngredientePublic(SQLModel):
    """Response model: campos que se exponen al cliente."""
    id: int
    nombre: str
    es_alergeno: bool
    eliminado_en: Optional[datetime] = None


class IngredienteList(SQLModel):
    """Response model paginado para GET /ingredientes/"""
    data: List[IngredientePublic]
    total: int