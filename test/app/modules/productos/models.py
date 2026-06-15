"""
Módulo: app/modules/productos/models.py
========================================

Modelo de persistencia de Productos. Es el módulo que usamos como
"conejito de indias" para probar los middlewares, exception handlers y
rate limiting que vienen después.

Decisiones:
-----------
  - `precio` como `float` (más simple para el curso). En producción real,
    usaríamos `Decimal` para evitar errores de redondeo con dinero.
  - `stock` como `int` no negativo (constraint a nivel Schema y DB).
  - `categoria` como `str` libre (no FK a tabla categorías) para
    simplificar; podría ser un enum o relación en una v2.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Producto(SQLModel, table=True):
    """
    Tabla `producto` en la base de datos.

    Campos:
      - id: PK autoincremental.
      - nombre: índice para búsquedas por nombre.
      - precio: validado > 0 a nivel Schema.
      - stock: validado >= 0 a nivel Schema.
      - categoria: string libre, indexado para filtrar.
      - created_at / updated_at: auditoría.
    """

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    nombre: str = Field(
        min_length=1,
        max_length=120,
        index=True,
        description="Nombre del producto. 1-120 chars, único (case-insensitive en Service).",
    )

    descripcion: str = Field(
        default="",
        max_length=500,
        description="Descripción opcional del producto.",
    )

    # ⚠️ En un sistema real, dinero va con Decimal para evitar errores
    # binarios. Para este curso educativo, `float` es suficiente.
    precio: float = Field(
        ge=0,
        description="Precio unitario. Validado >= 0 (0 = gratis).",
    )

    stock: int = Field(
        default=0,
        ge=0,
        description="Cantidad en stock. No puede ser negativo.",
    )

    categoria: str = Field(
        default="general",
        max_length=50,
        index=True,
        description="Categoría del producto. String libre (default 'general').",
    )

    is_active: bool = Field(
        default=True,
        description="Soft delete: False = producto descontinuado.",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Fecha de creación (UTC).",
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Fecha de última actualización (UTC).",
    )

    def __repr__(self) -> str:
        return f"Producto(id={self.id}, nombre='{self.nombre}', precio={self.precio}, stock={self.stock})"
