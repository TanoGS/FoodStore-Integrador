from datetime import datetime, timezone
from typing import Optional
from core.exceptions import NotFoundError, ForbiddenError, UnauthorizedError, BadRequestError, ConflictError, UnprocessableError, ServiceUnavailableError, BadGatewayError
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
                **data.model_dump(exclude={"categoria_ids", "receta", "precio_manual", "costo_produccion_manual"})
            )

            # Asignar categorías del menú
            for cat_id in data.categoria_ids:
                cat = uow.categorias.get_by_id(cat_id)
                if not cat:
                    raise NotFoundError(f"Categoría {cat_id} no encontrada",
                    )
                producto.categorias.append(cat)

            # Escandallo: cálculo de costo de producción
            costo_total = 0.0
            for item in data.receta:
                ing = uow.ingredientes.get_activo(item.ingrediente_id)
                if not ing:
                    raise NotFoundError(f"Ingrediente {item.ingrediente_id} no encontrado",
                    )
                costo_total += item.cantidad_requerida * float(ing.costo_unitario)
                enlace = ProductoIngrediente(
                    ingrediente_id=ing.id,
                    cantidad_requerida=item.cantidad_requerida,
                    es_removible=item.es_removible,
                )
                producto.ingredientes_enlaces.append(enlace)

            # Usar costo manual si se proporcionó, sino usar el calculado de ingredientes
            producto.costo_produccion = data.costo_produccion_manual if data.costo_produccion_manual is not None else costo_total

            if data.precio_manual is not None:
                producto.precio = data.precio_manual
            else:
                producto.precio = float(producto.costo_produccion) * (1 + float(producto.margen_ganancia) / 100)

            # RN: el precio final debe ser mayor a 0
            if producto.precio <= 0:
                raise BadRequestError("El precio del producto no puede ser 0. Ingresá un precio manual o configurá la receta y el margen.",
                )

            uow.productos.add(producto)
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
            raise NotFoundError("Producto no encontrado",
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
                raise NotFoundError("Producto no encontrado",
                )

            update_data = data.model_dump(exclude_unset=True)

            # Si cambian las categorías, reemplazarlas
            if "categoria_ids" in update_data:
                producto.categorias.clear()
                for cat_id in data.categoria_ids:
                    cat = uow.categorias.get_by_id(cat_id)
                    if not cat:
                        raise NotFoundError(f"Categoría {cat_id} no encontrada",
                        )
                    producto.categorias.append(cat)

            # Si cambia la receta, recalcular escandallo
            costo_total = 0.0
            if "receta" in update_data:
                # Con cascade="all, delete-orphan" en el modelo, .clear()
                # elimina los hijos de la DB automáticamente al hacer flush/commit
                producto.ingredientes_enlaces.clear()
                self._session.flush()

                for item in data.receta:
                    ing = uow.ingredientes.get_activo(item.ingrediente_id)
                    if not ing:
                        raise NotFoundError(f"Ingrediente {item.ingrediente_id} no encontrado",
                        )
                    costo_total += item.cantidad_requerida * float(ing.costo_unitario)
                    enlace = ProductoIngrediente(
                        ingrediente_id=ing.id,
                        cantidad_requerida=item.cantidad_requerida,
                        es_removible=item.es_removible,
                    )
                    producto.ingredientes_enlaces.append(enlace)

            # Usar costo manual si se proporcionó, sino usar el calculado de ingredientes
            costo_produccion_manual = update_data.get("costo_produccion_manual")
            if costo_produccion_manual is not None:
                producto.costo_produccion = costo_produccion_manual
            elif "receta" in update_data:
                producto.costo_produccion = costo_total

            # Aplicar margen_ganancia ANTES de recalcular precio para que el nuevo valor esté disponible
            if "margen_ganancia" in update_data:
                producto.margen_ganancia = update_data["margen_ganancia"]

            precio_manual = update_data.get("precio_manual")
            # Precedencia explícita:
            # 1. precio_manual → precio directo, no importan margen ni costo
            # 2. Sin precio_manual pero cambió costo/receta/margen → recalcular
            if precio_manual is not None:
                producto.precio = precio_manual
            elif costo_produccion_manual is not None or "receta" in update_data or "margen_ganancia" in update_data:
                producto.precio = float(producto.costo_produccion) * (1 + float(producto.margen_ganancia) / 100)

            # Resto de campos escalares (margen_ganancia ya fue aplicado arriba)
            for key, value in update_data.items():
                if key not in {"receta", "categoria_ids", "precio_manual", "costo_produccion_manual", "margen_ganancia"}:
                    setattr(producto, key, value)

            producto.actualizado_en = datetime.now(timezone.utc)
            uow.productos.add(producto)
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
                raise NotFoundError("Producto no encontrado",
                )
            producto.activo = activo
            producto.actualizado_en = datetime.now(timezone.utc)
            uow.productos.add(producto)
            self._session.flush()
            result = uow.productos.get_activo(producto.id)
        return ProductoPublic.model_validate(result)

    # ------------------------------------------------------------------
    def eliminar_producto(self, producto_id: int) -> None:
        uow = ProductoUnitOfWork(self._session)
        with uow:
            producto = uow.productos.get_activo(producto_id)
            if not producto:
                raise NotFoundError("Producto no encontrado",
                )
            producto.eliminado_en = datetime.now(timezone.utc)
            uow.productos.add(producto)

    # ------------------------------------------------------------------
    def reactivar_producto(self, producto_id: int) -> ProductoPublic:
        """Restaura un producto dado de baja (limpia eliminado_en)."""
        uow = ProductoUnitOfWork(self._session)
        with uow:
            producto = uow.productos.get_by_id(producto_id)
            if not producto:
                raise NotFoundError("Producto no encontrado",
                )
            producto.eliminado_en = None
            producto.actualizado_en = datetime.now(timezone.utc)
            uow.productos.add(producto)
            self._session.flush()
            result = uow.productos.get_by_id(producto.id)
        return ProductoPublic.model_validate(result)

    # ------------------------------------------------------------------
    def actualizar_imagenes(self, producto_id: int, imagenes_url: list[str]) -> ProductoPublic:
        """
        Reemplaza el array imagenes_url[] del producto (spec sección 6.3 / 5.2).
        Enviar una lista vacía elimina todas las imágenes.
        """
        uow = ProductoUnitOfWork(self._session)
        with uow:
            producto = uow.productos.get_activo(producto_id)
            if not producto:
                raise NotFoundError("Producto no encontrado")
            producto.imagenes_url = imagenes_url
            producto.actualizado_en = datetime.now(timezone.utc)
            uow.productos.add(producto)
            self._session.flush()
            result = uow.productos.get_activo(producto.id)
        return ProductoPublic.model_validate(result)

