from fastapi import APIRouter, Depends, status
from typing import List
from sqlmodel import Session

from core.database import get_session
from .schemas import CategoriaCreate, CategoriaResponse, CategoriaUpdate
from .unit_of_work import CategoriaUnitOfWork
from .service import CategoriaService

router = APIRouter(prefix="/categorias", tags=["Categorías"])

def get_categoria_service(session: Session = Depends(get_session)) -> CategoriaService:
    uow = CategoriaUnitOfWork(session)
    return CategoriaService(uow)

@router.post("/", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED)
def crear_categoria(
    categoria_in: CategoriaCreate,
    service: CategoriaService = Depends(get_categoria_service)
):
    return service.crear(categoria_in)

@router.get("/", response_model=List[CategoriaResponse], status_code=status.HTTP_200_OK)
def listar_categorias(
    service: CategoriaService = Depends(get_categoria_service)
):
    return service.listar_activas()

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def eliminar_categoria(
    id: int,
    service: CategoriaService = Depends(get_categoria_service)
):
    return service.eliminar_logicamente(id)

@router.patch("/{id}", response_model=CategoriaResponse, status_code=status.HTTP_200_OK)
def actualizar_categoria(
    id: int,
    categoria_in: CategoriaUpdate,
    service: CategoriaService = Depends(get_categoria_service)
):
    return service.actualizar(id, categoria_in)