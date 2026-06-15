"""
Módulo: app/modules/productos/service.py
=========================================

Lógica de negocio de Productos (refactorizado al patrón del modelo:
session en __init__, UoW por método con `with`).
"""

from datetime import datetime

from sqlmodel import Session

from app.core.exceptions.custom_exceptions import (
    AuthorizationError,
    BusinessRuleError,
    DuplicateResourceError,
    ResourceNotFoundError,
)
from app.modules.productos.models import Producto
from app.modules.productos.schemas import (
    ProductoCreate,
    ProductoList,
    ProductoPublic,
    ProductoUpdate,
)
from app.modules.productos.unit_of_work import ProductoUnitOfWork


class ProductoService:
    """
    Lógica de negocio de Productos.

    El Service recibe la session en su __init__ (inyectada por el
    router). Cada método abre su propio UoW con `with ... as uow:`
    para delimitar la transacción.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # =======================================================================
    # create
    # =======================================================================
    def create(self, payload: ProductoCreate) -> ProductoPublic:
        """
        Crea un producto. Verifica unicidad del nombre (case-insensitive).
        """
        with ProductoUnitOfWork(self._session) as uow:
            # Unicidad case-insensitive. Traemos todos los que matcheen
            # parcialmente y comparamos en lower.
            existing = uow.productos.search(
                nombre=payload.nombre,
                only_active=False,  # incluir desactivados para detectar duplicados
            )
            if any(p.nombre.lower() == payload.nombre.lower() for p in existing):
                raise DuplicateResourceError(
                    resource="producto",
                    field="nombre",
                    value=payload.nombre,
                )

            producto = Producto(
                nombre=payload.nombre,
                descripcion=payload.descripcion,
                precio=payload.precio,
                stock=payload.stock,
                categoria=payload.categoria,
                is_active=True,
            )
            uow.productos.add(producto)
            return ProductoPublic.model_validate(producto)

    # =======================================================================
    # get_by_id
    # =======================================================================
    def get_by_id(
        self,
        producto_id: int,
        include_inactive: bool = False,
    ) -> ProductoPublic:
        """
        Obtiene un producto por ID. 404 si no existe o está inactivo
        (y include_inactive=False).
        """
        with ProductoUnitOfWork(self._session) as uow:
            producto = uow.productos.get_by_id(producto_id)
            if producto is None:
                raise ResourceNotFoundError(
                    resource="producto",
                    identifier=str(producto_id),
                )
            if not include_inactive and not producto.is_active:
                raise ResourceNotFoundError(
                    resource="producto",
                    identifier=str(producto_id),
                )
            return ProductoPublic.model_validate(producto)

    # =======================================================================
    # search
    # =======================================================================
    def search(
        self,
        nombre: str | None = None,
        categoria: str | None = None,
        min_precio: float | None = None,
        max_precio: float | None = None,
        skip: int = 0,
        limit: int = 100,
        only_active: bool = True,
    ) -> ProductoList:
        """
        Busca productos con filtros opcionales.

        Valida que min_precio <= max_precio (regla cross-field).
        """
        # Validación cross-field ANTES de tocar la DB.
        if min_precio is not None and max_precio is not None and min_precio > max_precio:
            raise BusinessRuleError(
                f"min_precio ({min_precio}) no puede ser mayor que max_precio ({max_precio})."
            )

        with ProductoUnitOfWork(self._session) as uow:
            items = uow.productos.search(
                nombre=nombre,
                categoria=categoria,
                min_precio=min_precio,
                max_precio=max_precio,
                skip=skip,
                limit=limit,
                only_active=only_active,
            )
            total = uow.productos.count_search(
                nombre=nombre,
                categoria=categoria,
                min_precio=min_precio,
                max_precio=max_precio,
                only_active=only_active,
            )
            return ProductoList(
                items=[ProductoPublic.model_validate(p) for p in items],
                total=total,
            )

    # =======================================================================
    # update
    # =======================================================================
    def update(
        self,
        producto_id: int,
        payload: ProductoUpdate,
        is_admin: bool,
    ) -> ProductoPublic:
        """
        Actualiza un producto.

        Reglas:
          - `is_active` solo lo puede cambiar un admin.
          - Si cambia `nombre`, validar unicidad case-insensitive.
        """
        with ProductoUnitOfWork(self._session) as uow:
            producto = uow.productos.get_by_id(producto_id)
            if producto is None:
                raise ResourceNotFoundError(
                    resource="producto",
                    identifier=str(producto_id),
                )

            if payload.is_active is not None and not is_admin:
                raise AuthorizationError(
                    "Solo un administrador puede descontinuar/reactivar productos."
                )

            update_data = payload.model_dump(exclude_unset=True)

            # Si cambia el nombre, validar unicidad.
            if "nombre" in update_data and update_data["nombre"] != producto.nombre:
                new_name = update_data["nombre"]
                existing = uow.productos.search(
                    nombre=new_name, only_active=False
                )
                if any(
                    p.nombre.lower() == new_name.lower() and p.id != producto_id
                    for p in existing
                ):
                    raise DuplicateResourceError(
                        resource="producto",
                        field="nombre",
                        value=new_name,
                    )

            update_data["updated_at"] = datetime.utcnow()
            for key, value in update_data.items():
                setattr(producto, key, value)
            updated = uow.productos.update(producto)
            return ProductoPublic.model_validate(updated)

    # =======================================================================
    # set_active (soft delete / undelete)
    # =======================================================================
    def set_active(
        self,
        producto_id: int,
        is_active: bool,
        is_admin: bool,
    ) -> ProductoPublic:
        """
        Activa/descontinua un producto. Solo admin.
        """
        if not is_admin:
            raise AuthorizationError(
                "Solo un administrador puede descontinuar/reactivar productos."
            )
        with ProductoUnitOfWork(self._session) as uow:
            producto = uow.productos.get_by_id(producto_id)
            if producto is None:
                raise ResourceNotFoundError(
                    resource="producto",
                    identifier=str(producto_id),
                )
            # Mutamos la entidad en su lugar (patrón SQLAlchemy identity map).
            # `model_copy` crea un nuevo objeto que SQLAlchemy a veces no
            # reconcilea bien con la session → la actualización no se persiste.
            producto.is_active = is_active
            producto.updated_at = datetime.utcnow()
            updated = uow.productos.update(producto)
            return ProductoPublic.model_validate(updated)
