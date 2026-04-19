from fastapi import HTTPException, status
from datetime import datetime, timezone
from .schemas import IngredienteCreate, IngredienteUpdate
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

    def actualizar(self, id: int, data: IngredienteUpdate) -> Ingrediente:
        ingrediente = self.uow.ingredientes.get_by_id(id)
        if not ingrediente or ingrediente.eliminado_en is not None:
            raise HTTPException(status_code=404, detail="Ingrediente no encontrado.")

        if data.nombre and data.nombre != ingrediente.nombre:
            if self.uow.ingredientes.get_by_nombre(data.nombre):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Ya existe otro ingrediente con este nombre."
                )

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(ingrediente, key, value)

        try:
            self.uow.commit()
            self.uow.session.refresh(ingrediente)
            return ingrediente
        except Exception as e:
            self.uow.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    def eliminar_logicamente(self, id: int):
        ingrediente = self.uow.ingredientes.get_by_id(id)
        if not ingrediente or ingrediente.eliminado_en is not None:
            raise HTTPException(status_code=404, detail="Ingrediente no encontrado.")

        try:
            ingrediente.eliminado_en = datetime.now(timezone.utc)
            self.uow.commit()
            return {"message": f"Ingrediente '{ingrediente.nombre}' eliminado correctamente."}
        except Exception as e:
            self.uow.rollback()
            raise HTTPException(status_code=500, detail=str(e))