from fastapi import HTTPException, status
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Session

from .unit_of_work import CategoriaUnitOfWork
from .models import Categoria
from .schemas import CategoriaCreate, CategoriaUpdate, CategoriaPublic


class CategoriaService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    def crear_categoria(self, data: CategoriaCreate) -> CategoriaPublic:
        uow = CategoriaUnitOfWork(self._session)
        with uow:
            if data.parent_id:
                parent = uow.categorias.get_by_id(data.parent_id)
                if not parent:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Categoría padre no encontrada",
                    )
            categoria = Categoria(**data.model_dump())
            result = uow.categorias.add(categoria)
        return CategoriaPublic.model_validate(result)

    # ------------------------------------------------------------------
    def listar_categorias(
        self,
        parent_id: Optional[int] = None,
        solo_raiz: bool = False,
        skip: int = 0,
        limit: int = 200,
        incluir_eliminados: bool = False,
    ) -> list[CategoriaPublic]:
        uow = CategoriaUnitOfWork(self._session)
        with uow:
            if incluir_eliminados:
                categorias = uow.categorias.get_all_incluir_eliminados(skip, limit)
            elif parent_id is not None:
                categorias = uow.categorias.get_by_parent_id(parent_id, skip, limit)
            elif solo_raiz:
                categorias = uow.categorias.get_all_raiz(skip, limit)
            else:
                categorias = uow.categorias.get_all_activos(skip, limit)
            # Filtrar sub-categorías inactivas/eliminadas en el árbol eager-loaded
            if not incluir_eliminados:
                for cat in categorias:
                    cat.subcategorias = [
                        sub for sub in (cat.subcategorias or [])
                        if sub.activo and sub.eliminado_en is None
                    ]
        return [CategoriaPublic.model_validate(c) for c in categorias]

    # ------------------------------------------------------------------
    def obtener_categoria(self, categoria_id: int) -> CategoriaPublic:
        uow = CategoriaUnitOfWork(self._session)
        with uow:
            categoria = uow.categorias.get_activo(categoria_id)
        if not categoria:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoría no encontrada",
            )
        return CategoriaPublic.model_validate(categoria)

    # ------------------------------------------------------------------
    def actualizar_categoria(
        self, categoria_id: int, data: CategoriaUpdate
    ) -> CategoriaPublic:
        uow = CategoriaUnitOfWork(self._session)
        with uow:
            categoria = uow.categorias.get_activo(categoria_id)
            if not categoria:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Categoría no encontrada",
                )
            for key, value in data.model_dump(exclude_unset=True).items():
                setattr(categoria, key, value)
            categoria.actualizado_en = datetime.now(timezone.utc)
            result = uow.categorias.add(categoria)
        return CategoriaPublic.model_validate(result)

    # ------------------------------------------------------------------
    def reactivar_categoria(self, categoria_id: int) -> CategoriaPublic:
        uow = CategoriaUnitOfWork(self._session)
        with uow:
            categoria = uow.categorias.get_eliminado(categoria_id)
            if not categoria:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Categoría eliminada no encontrada.",
                )
            # RN: si tiene padre, el padre debe estar activo
            if categoria.parent_id is not None:
                padre = uow.categorias.get_activo(categoria.parent_id)
                if not padre:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="No se puede reactivar: la categoría padre está eliminada.",
                    )
            categoria.eliminado_en = None
            categoria.actualizado_en = datetime.now(timezone.utc)
            result = uow.categorias.add(categoria)
        return CategoriaPublic.model_validate(result)

    # ------------------------------------------------------------------
    def eliminar_categoria(self, categoria_id: int) -> None:
        uow = CategoriaUnitOfWork(self._session)
        with uow:
            categoria = uow.categorias.get_activo(categoria_id)
            if not categoria:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Categoría no encontrada",
                )
            # RN: no se puede eliminar si tiene subcategorías activas
            if uow.categorias.has_active_children(categoria_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No se puede eliminar: la categoría tiene subcategorías activas.",
                )
            # RN: no se puede eliminar si tiene productos activos (HTTP 409)
            if uow.categorias.has_active_products(categoria_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No se puede eliminar: la categoría tiene productos activos asociados.",
                )
            categoria.eliminado_en = datetime.now(timezone.utc)
            categoria.actualizado_en = datetime.now(timezone.utc)
            uow.categorias.add(categoria)
