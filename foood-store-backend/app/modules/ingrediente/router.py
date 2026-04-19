from fastapi import APIRouter, Depends, status
from typing import List
from sqlmodel import Session

from core.database import get_session
from .schemas import IngredienteCreate, IngredienteResponse, IngredienteUpdate
from .unit_of_work import IngredienteUnitOfWork
from .service import IngredienteService

router = APIRouter(prefix="/ingredientes", tags=["Ingredientes"])

def get_ingrediente_service(session: Session = Depends(get_session)) -> IngredienteService:
    uow = IngredienteUnitOfWork(session)
    return IngredienteService(uow)

@router.post("/", response_model=IngredienteResponse, status_code=status.HTTP_201_CREATED)
def crear_ingrediente(ingrediente_in: IngredienteCreate, service: IngredienteService = Depends(get_ingrediente_service)):
    return service.crear(ingrediente_in)

@router.get("/", response_model=List[IngredienteResponse], status_code=status.HTTP_200_OK)
def listar_ingredientes(service: IngredienteService = Depends(get_ingrediente_service)):
    return service.listar_activos()

@router.patch("/{id}", response_model=IngredienteResponse, status_code=status.HTTP_200_OK)
def actualizar_ingrediente(id: int, ingrediente_in: IngredienteUpdate, service: IngredienteService = Depends(get_ingrediente_service)):
    return service.actualizar(id, ingrediente_in)

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def eliminar_ingrediente(id: int, service: IngredienteService = Depends(get_ingrediente_service)):
    return service.eliminar_logicamente(id)