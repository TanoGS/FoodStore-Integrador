from fastapi import HTTPException, status
from datetime import datetime, timezone
from .schemas import IngredienteCreate
from .models import Ingrediente
from .unit_of_work import IngredienteUnitOfWork

class IngredienteService:
    def __init__(self, uow: IngredienteUnitOfWork):
        self.uow = uow

    def crear(self, data: IngredienteCreate) -> Ingrediente:
        if self.uow.ingredientes.get_by_nombre(data.nombre):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Ya existe un ingrediente con este nombre."
            )

        try:
            nuevo_ingrediente = Ingrediente(**data.model_dump())
            self.uow.ingredientes.add(nuevo_ingrediente)
            self.uow.commit()
            self.uow.session.refresh(nuevo_ingrediente)
            return nuevo_ingrediente
        except Exception as e:
            self.uow.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    def listar_activos(self) -> list[Ingrediente]:
        return self.uow.ingredientes.get_all_activos()