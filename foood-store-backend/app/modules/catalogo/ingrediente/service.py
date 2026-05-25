from fastapi import HTTPException, status
from datetime import datetime, timezone
from sqlmodel import Session

from .unit_of_work import IngredienteUnitOfWork
from .models import Ingrediente
from .schemas import (
    IngredienteCreate,
    IngredienteUpdate,
    IngredientePublic,
)


class IngredienteService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Ingrediente
    # ------------------------------------------------------------------
    def crear_ingrediente(self, data: IngredienteCreate) -> IngredientePublic:
        uow = IngredienteUnitOfWork(self._session)
        with uow:
            ingrediente = Ingrediente(**data.model_dump())
            result = uow.ingredientes.add(ingrediente)
        return IngredientePublic.model_validate(result)

    def listar_ingredientes(
        self, offset: int = 0, limit: int = 50, incluir_eliminados: bool = False
    ) -> list[IngredientePublic]:
        uow = IngredienteUnitOfWork(self._session)
        with uow:
            if incluir_eliminados:
                ingredientes = uow.ingredientes.get_all_incluir_eliminados(offset, limit)
            else:
                ingredientes = uow.ingredientes.get_all_activos(offset, limit)
        return [IngredientePublic.model_validate(i) for i in ingredientes]

    def obtener_ingrediente(self, ingrediente_id: int) -> IngredientePublic:
        uow = IngredienteUnitOfWork(self._session)
        with uow:
            ingrediente = uow.ingredientes.get_activo(ingrediente_id)
        if not ingrediente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ingrediente no encontrado",
            )
        return IngredientePublic.model_validate(ingrediente)

    def actualizar_ingrediente(
        self, ingrediente_id: int, data: IngredienteUpdate
    ) -> IngredientePublic:
        uow = IngredienteUnitOfWork(self._session)
        with uow:
            ingrediente = uow.ingredientes.get_activo(ingrediente_id)
            if not ingrediente:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ingrediente no encontrado",
                )
            for key, value in data.model_dump(exclude_unset=True).items():
                setattr(ingrediente, key, value)
            ingrediente.actualizado_en = datetime.now(timezone.utc)
            result = uow.ingredientes.add(ingrediente)
        return IngredientePublic.model_validate(result)

    def eliminar_ingrediente(self, ingrediente_id: int) -> None:
        uow = IngredienteUnitOfWork(self._session)
        with uow:
            ingrediente = uow.ingredientes.get_activo(ingrediente_id)
            if not ingrediente:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ingrediente no encontrado",
                )
            ingrediente.eliminado_en = datetime.now(timezone.utc)
            ingrediente.actualizado_en = datetime.now(timezone.utc)
            uow.ingredientes.add(ingrediente)

    def reactivar_ingrediente(self, ingrediente_id: int) -> IngredientePublic:
        """Limpia eliminado_en para restaurar un ingrediente dado de baja."""
        uow = IngredienteUnitOfWork(self._session)
        with uow:
            # Usamos get_by_id (sin filtro de eliminado) para encontrarlo
            ingrediente = uow.ingredientes.get_by_id(ingrediente_id)
            if not ingrediente:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ingrediente no encontrado",
                )
            ingrediente.eliminado_en = None
            ingrediente.actualizado_en = datetime.now(timezone.utc)
            result = uow.ingredientes.add(ingrediente)
        return IngredientePublic.model_validate(result)
