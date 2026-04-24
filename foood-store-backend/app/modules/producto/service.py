# app/modules/producto/service.py
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.producto.models import Producto
from app.modules.producto.schemas import (
    ProductoCreate, ProductoUpdate, ProductoPublic, ProductoList,
)
from app.modules.producto.unit_of_work import ProductoUnitOfWork


class ProductoService:
    """
    Capa de lógica de negocio para Productos.

    Responsabilidades:
    - Validaciones de dominio (nombre único, categorías válidas, etc.)
    - Coordinar repositorios a través del UoW
    - Levantar HTTPException cuando corresponde
    - NUNCA acceder directamente a la Session
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ──────────────────────────────────────────────────────────────────

    def _get_or_404(self, uow: ProductoUnitOfWork, producto_id: int) -> Producto:
        producto = uow.productos.get_by_id(producto_id)
        if not producto or producto.eliminado_en is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con id={producto_id} no encontrado.",
            )
        return producto

    def _assert_nombre_unique(self, uow: ProductoUnitOfWork, nombre: str) -> None:
        if uow.productos.get_by_nombre(nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un producto con el nombre '{nombre}'.",
            )

    # ── Casos de uso ─────────────────────────────────────────────────────────────────

    def crear(self, data: ProductoCreate) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:
            self._assert_nombre_unique(uow, data.nombre)

            prod_dict = data.model_dump(exclude={"categoria_ids"})
            nuevo_producto = Producto.model_validate(prod_dict)

            if data.categoria_ids:
                for cat_id in data.categoria_ids:
                    categoria = uow.categorias.get_by_id(cat_id)
                    if not categoria or categoria.eliminado_en:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Categoría con id={cat_id} no válida.",
                        )
                    nuevo_producto.categorias.append(categoria)

            uow.productos.add(nuevo_producto)
            result = ProductoPublic.model_validate(nuevo_producto)

        return result

    def listar_activos(self, offset: int = 0, limit: int = 20) -> ProductoList:
        with ProductoUnitOfWork(self._session) as uow:
            productos = uow.productos.get_all_activos(offset=offset, limit=limit)
            total = uow.productos.count_activos()
            result = ProductoList(
                data=[ProductoPublic.model_validate(p) for p in productos],
                total=total,
            )
        return result

    def obtener_por_id(self, producto_id: int) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            result = ProductoPublic.model_validate(producto)
        return result

    def actualizar(self, producto_id: int, data: ProductoUpdate) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            if data.nombre and data.nombre != producto.nombre:
                self._assert_nombre_unique(uow, data.nombre)

            patch = data.model_dump(exclude_unset=True, exclude={"categoria_ids"})
            for field, value in patch.items():
                setattr(producto, field, value)

            if data.categoria_ids is not None:
                producto.categorias = []
                for cat_id in data.categoria_ids:
                    cat = uow.categorias.get_by_id(cat_id)
                    if cat:
                        producto.categorias.append(cat)

            uow.productos.add(producto)
            result = ProductoPublic.model_validate(producto)

        return result

    def eliminar_logicamente(self, producto_id: int) -> dict:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            producto.eliminado_en = datetime.now(timezone.utc)
            uow.productos.add(producto)
            nombre = producto.nombre  # capturar antes del commit

        return {"message": f"Producto '{nombre}' eliminado correctamente."}