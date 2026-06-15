from fastapi import HTTPException, status
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Session

from .unit_of_work import ProductoUnitOfWork
from .models import Producto
from .schemas import ProductoCreate, ProductoUpdate, ProductoPublic
from app.modules.catalogo.shared_models import ProductoIngrediente


class ProductoService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    def crear_producto(self, data: ProductoCreate) -> ProductoPublic:
        uow = ProductoUnitOfWork(self._session)
        with uow:
            producto = Producto(
                **data.model_dump(exclude={"categoria_ids", "receta", "precio_manual"})
            )

            # Asignar categorías del menú
            for cat_id in data.categoria_ids:
                cat = uow.categorias.get_by_id(cat_id)
                if not cat:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Categoría {cat_id} no encontrada",
                    )
                producto.categorias.append(cat)

            # Escandallo: cálculo de costo de producción
            costo_total = 0.0
            for item in data.receta:
                ing = uow.ingredientes.get_activo(item.ingrediente_id)
                if not ing:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Ingrediente {item.ingrediente_id} no encontrado",
                    )
                costo_total += item.cantidad_requerida * float(ing.costo_unitario)
                enlace = ProductoIngrediente(
                    ingrediente_id=ing.id,
                    cantidad_requerida=item.cantidad_requerida,
                    es_removible=item.es_removible,
                )
                producto.ingredientes_enlaces.append(enlace)

            producto.costo_produccion = costo_total

            if data.precio_manual is not None:
                producto.precio = data.precio_manual
            else:
                producto.precio = costo_total * (1 + float(producto.margen_ganancia) / 100)

            self._session.add(producto)
            self._session.flush()
            result = uow.productos.get_activo(producto.id)

        return ProductoPublic.model_validate(result)

    # ------------------------------------------------------------------
    def listar_productos(
        self,
        categoria_id: Optional[int] = None,
        activo: Optional[bool] = None,
        q: Optional[str] = None,
        skip: int = 0,
        limit: int = 200,
        incluir_eliminados: bool = False,
    ) -> list[ProductoPublic]:
        uow = ProductoUnitOfWork(self._session)
        with uow:
            if incluir_eliminados:
                productos = uow.productos.get_all_incluir_eliminados(skip, limit)
            else:
                productos = uow.productos.get_filtrado(
                    categoria_id=categoria_id,
                    activo=activo,
                    q=q,
                    skip=skip,
                    limit=limit,
                )
        return [ProductoPublic.model_validate(p) for p in productos]

    # ------------------------------------------------------------------
    def obtener_producto(self, producto_id: int) -> ProductoPublic:
        uow = ProductoUnitOfWork(self._session)
        with uow:
            producto = uow.productos.get_activo(producto_id)
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado",
            )
        return ProductoPublic.model_validate(producto)

    # ------------------------------------------------------------------
    def actualizar_producto(
        self, producto_id: int, data: ProductoUpdate
    ) -> ProductoPublic:
        uow = ProductoUnitOfWork(self._session)
        with uow:
            producto = uow.productos.get_activo(producto_id)
            if not producto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Producto no encontrado",
                )

            update_data = data.model_dump(exclude_unset=True)

            # Si cambian las categorías, reemplazarlas
            if "categoria_ids" in update_data:
                producto.categorias.clear()
                for cat_id in data.categoria_ids:
                    cat = uow.categorias.get_by_id(cat_id)
                    if not cat:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Categoría {cat_id} no encontrada",
                        )
                    producto.categorias.append(cat)

            # Si cambia la receta, recalcular escandallo
            if "receta" in update_data:
                # Con cascade="all, delete-orphan" en el modelo, .clear()
                # elimina los hijos de la DB automáticamente al hacer flush/commit
                producto.ingredientes_enlaces.clear()
                self._session.flush()

                costo_total = 0.0
                for item in data.receta:
                    ing = uow.ingredientes.get_activo(item.ingrediente_id)
                    if not ing:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Ingrediente {item.ingrediente_id} no encontrado",
                        )
                    costo_total += item.cantidad_requerida * float(ing.costo_unitario)
                    enlace = ProductoIngrediente(
                        ingrediente_id=ing.id,
                        cantidad_requerida=item.cantidad_requerida,
                        es_removible=item.es_removible,
                    )
                    producto.ingredientes_enlaces.append(enlace)

                producto.costo_produccion = costo_total
                precio_manual = update_data.get("precio_manual")
                if precio_manual is not None:
                    producto.precio = precio_manual
                else:
                    margen = update_data.get("margen_ganancia", producto.margen_ganancia)
                    producto.precio = costo_total * (1 + float(margen) / 100)

            # Resto de campos escalares
            for key, value in update_data.items():
                if key not in {"receta", "categoria_ids", "precio_manual"}:
                    setattr(producto, key, value)

            producto.actualizado_en = datetime.now(timezone.utc)
            self._session.add(producto)
            self._session.flush()
            result = uow.productos.get_activo(producto.id)

        return ProductoPublic.model_validate(result)

    # ------------------------------------------------------------------
    def toggle_disponibilidad(self, producto_id: int, activo: bool) -> ProductoPublic:
        """Activa o desactiva la disponibilidad operacional (ADMIN / GESTOR_STOCK)."""
        uow = ProductoUnitOfWork(self._session)
        with uow:
            producto = uow.productos.get_activo(producto_id)
            if not producto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Producto no encontrado",
                )
            producto.activo = activo
            producto.actualizado_en = datetime.now(timezone.utc)
            self._session.add(producto)
            self._session.flush()
            result = uow.productos.get_activo(producto.id)
        return ProductoPublic.model_validate(result)

    # ------------------------------------------------------------------
    def eliminar_producto(self, producto_id: int) -> None:
        uow = ProductoUnitOfWork(self._session)
        with uow:
            producto = uow.productos.get_activo(producto_id)
            if not producto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Producto no encontrado",
                )
            producto.eliminado_en = datetime.now(timezone.utc)
            self._session.add(producto)

    # ------------------------------------------------------------------
    def reactivar_producto(self, producto_id: int) -> ProductoPublic:
        """Restaura un producto dado de baja (limpia eliminado_en)."""
        uow = ProductoUnitOfWork(self._session)
        with uow:
            producto = uow.productos.get_by_id(producto_id)
            if not producto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Producto no encontrado",
                )
            producto.eliminado_en = None
            producto.actualizado_en = datetime.now(timezone.utc)
            self._session.add(producto)
            self._session.flush()
            result = uow.productos.get_by_id(producto.id)
        return ProductoPublic.model_validate(result)

