# app/modules/categoria/service.py
from fastapi import HTTPException, status
from datetime import datetime, timezone
from sqlmodel import Session

from app.modules.categoria.models import Categoria
from app.modules.categoria.schemas import (
    CategoriaCreate, CategoriaUpdate, CategoriaPublic, CategoriaList,
)
from app.modules.categoria.unit_of_work import CategoriaUnitOfWork


class CategoriaService:
    """
    Capa de lógica de negocio para Categorias.

    Responsabilidades:
    - Validaciones de dominio (nombre único, jerarquía, etc.)
    - Coordinar repositorios a través del UoW
    - Levantar HTTPException cuando corresponde
    - NUNCA acceder directamente a la Session

    REGLA IMPORTANTE — objetos ORM y commit():
    Después de que el UoW hace commit(), SQLAlchemy expira los atributos
    del objeto ORM. Toda serialización (model_dump / model_validate)
    debe ocurrir DENTRO del bloque `with uow:`, antes de que __exit__
    dispare el commit.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ──────────────────────────────────────────────────────────────────

    def _get_or_404(self, uow: CategoriaUnitOfWork, categoria_id: int) -> Categoria:
        categoria = uow.categorias.get_by_id(categoria_id)
        if not categoria or categoria.eliminado_en is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Categoría con id={categoria_id} no encontrada.",
            )
        return categoria

    def _assert_nombre_unique(self, uow: CategoriaUnitOfWork, nombre: str) -> None:
        if uow.categorias.get_by_nombre(nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una categoría con el nombre '{nombre}'.",
            )

    # ── Casos de uso ─────────────────────────────────────────────────────────────────

    def crear(self, data: CategoriaCreate) -> CategoriaPublic:
        with CategoriaUnitOfWork(self._session) as uow:
            if data.padre_id == 0:
                data.padre_id = None

            self._assert_nombre_unique(uow, data.nombre)

            if data.padre_id:
                padre = uow.categorias.get_by_id(data.padre_id)
                if not padre or padre.eliminado_en is not None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="La categoría padre indicada no existe o está eliminada.",
                    )

            nueva_categoria = Categoria.model_validate(data)
            uow.categorias.add(nueva_categoria)
            result = CategoriaPublic.model_validate(nueva_categoria)

        return result

    def listar_activas(self, offset: int = 0, limit: int = 20) -> CategoriaList:
        with CategoriaUnitOfWork(self._session) as uow:
            categorias = uow.categorias.get_all_activas(offset=offset, limit=limit)
            total = uow.categorias.count_activas()
            result = CategoriaList(
                data=[CategoriaPublic.model_validate(c) for c in categorias],
                total=total,
            )
        return result

    def obtener_por_id(self, categoria_id: int) -> CategoriaPublic:
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = self._get_or_404(uow, categoria_id)
            result = CategoriaPublic.model_validate(categoria)
        return result

    def actualizar(self, categoria_id: int, data: CategoriaUpdate) -> CategoriaPublic:
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = self._get_or_404(uow, categoria_id)

            if data.nombre and data.nombre != categoria.nombre:
                self._assert_nombre_unique(uow, data.nombre)

            if data.padre_id is not None:
                if data.padre_id == categoria_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Una categoría no puede ser subcategoría de sí misma.",
                    )
                padre = uow.categorias.get_by_id(data.padre_id)
                if not padre or padre.eliminado_en is not None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="La categoría padre indicada no existe o está eliminada.",
                    )

            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(categoria, field, value)

            uow.categorias.add(categoria)
            result = CategoriaPublic.model_validate(categoria)

        return result

    def eliminar_logicamente(self, categoria_id: int) -> dict:
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = self._get_or_404(uow, categoria_id)
            categoria.eliminado_en = datetime.now(timezone.utc)
            uow.categorias.add(categoria)
            nombre = categoria.nombre  # capturar antes del commit

        return {"message": f"Categoría '{nombre}' eliminada correctamente."}