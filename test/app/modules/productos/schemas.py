"""
Módulo: app/modules/productos/schemas.py
=========================================

Schemas Pydantic de Productos: lo que entra y sale por HTTP.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductoBase(BaseModel):
    """
    Campos comunes de Producto. Lo usan Create/Update/Read para evitar
    repetir definiciones.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(
        min_length=1,
        max_length=120,
        description="Nombre único del producto (case-insensitive).",
    )

    descripcion: str = Field(
        default="",
        max_length=500,
        description="Descripción opcional.",
    )

    precio: float = Field(
        ge=0,
        description="Precio unitario. >= 0.",
    )

    stock: int = Field(
        default=0,
        ge=0,
        description="Cantidad en stock. >= 0.",
    )

    categoria: str = Field(
        default="general",
        max_length=50,
        description="Categoría del producto.",
    )


class ProductoCreate(ProductoBase):
    """Schema de entrada: lo que el cliente manda para crear un producto."""
    pass


class ProductoUpdate(BaseModel):
    """
    Schema de actualización parcial (PATCH). Todos los campos opcionales.
    El cliente envía solo los que quiere cambiar.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nombre: Optional[str] = Field(
        default=None, min_length=1, max_length=120,
        description="Nuevo nombre.",
    )
    descripcion: Optional[str] = Field(
        default=None, max_length=500,
        description="Nueva descripción.",
    )
    precio: Optional[float] = Field(
        default=None, ge=0,
        description="Nuevo precio.",
    )
    stock: Optional[int] = Field(
        default=None, ge=0,
        description="Nuevo stock.",
    )
    categoria: Optional[str] = Field(
        default=None, max_length=50,
        description="Nueva categoría.",
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Activar/descontinuar producto. Solo admin.",
    )


class ProductoPublic(ProductoBase):
    """
    Schema de salida (read). Incluye `id` y timestamps.
    NUNCA exponemos campos privados porque Producto no tiene.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductoList(BaseModel):
    """
    Respuesta paginada de la lista de productos.
    Mismo formato que UserList: items + total.
    """
    items: list[ProductoPublic]
    total: int = Field(ge=0, description="Cantidad total de productos activos.")
