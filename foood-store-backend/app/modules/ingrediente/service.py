# app/modules/ingrediente/service.py
from fastapi import HTTPException, status
from datetime import datetime, timezone
from sqlmodel import Session

from app.modules.ingrediente.models import Ingrediente
from app.modules.ingrediente.schemas import (
    IngredienteCreate, IngredienteUpdate, IngredientePublic, IngredienteList,
)
from app.modules.ingrediente.unit_of_work import IngredienteUnitOfWork


class IngredienteService:
    """
    Capa de lógica de negocio para Ingredientes.

    Responsabilidades:
    - Validaciones de dominio (nombre único, etc.)
    - Coordinar repositorios a través del UoW
    - Levantar HTTPException cuando corresponde
    - NUNCA acceder directamente a la Session
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ──────────────────────────────────────────────────────────────────

    def _get_or_404(self, uow: IngredienteUnitOfWork, ingrediente_id: int) -> Ingrediente:
        ingrediente = uow.ingredientes.get_by_id(ingrediente_id)
        if not ingrediente or ingrediente.eliminado_en is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ingrediente con id={ingrediente_id} no encontrado.",
            )
        return ingrediente

    def _assert_nombre_unique(self, uow: IngredienteUnitOfWork, nombre: str) -> None:
        if uow.ingredientes.get_by_nombre(nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un ingrediente con el nombre '{nombre}'.",
            )

    # ── Casos de uso ─────────────────────────────────────────────────────────────────

    def crear(self, data: IngredienteCreate) -> IngredientePublic:
        with IngredienteUnitOfWork(self._session) as uow:
            self._assert_nombre_unique(uow, data.nombre)
            nuevo = Ingrediente.model_validate(data)
            uow.ingredientes.add(nuevo)
            result = IngredientePublic.model_validate(nuevo)
        return result

    def listar_activos(self, offset: int = 0, limit: int = 20) -> IngredienteList:
        with IngredienteUnitOfWork(self._session) as uow:
            ingredientes = uow.ingredientes.get_all_activos(offset=offset, limit=limit)
            total = uow.ingredientes.count_activos()
            result = IngredienteList(
                data=[IngredientePublic.model_validate(i) for i in ingredientes],
                total=total,
            )
        return result

    def obtener_por_id(self, ingrediente_id: int) -> IngredientePublic:
        with IngredienteUnitOfWork(self._session) as uow:
            ingrediente = self._get_or_404(uow, ingrediente_id)
            result = IngredientePublic.model_validate(ingrediente)
        return result

    def actualizar(self, ingrediente_id: int, data: IngredienteUpdate) -> IngredientePublic:
        with IngredienteUnitOfWork(self._session) as uow:
            ingrediente = self._get_or_404(uow, ingrediente_id)

            if data.nombre and data.nombre != ingrediente.nombre:
                self._assert_nombre_unique(uow, data.nombre)

            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(ingrediente, field, value)

            uow.ingredientes.add(ingrediente)
            result = IngredientePublic.model_validate(ingrediente)

        return result

    def eliminar_logicamente(self, ingrediente_id: int) -> dict:
        with IngredienteUnitOfWork(self._session) as uow:
            ingrediente = self._get_or_404(uow, ingrediente_id)
            ingrediente.eliminado_en = datetime.now(timezone.utc)
            uow.ingredientes.add(ingrediente)
            nombre = ingrediente.nombre  # capturar antes del commit

        return {"message": f"Ingrediente '{nombre}' eliminado correctamente."}