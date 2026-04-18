from fastapi import APIRouter, Depends, status
from typing import List
from sqlmodel import Session

from core.database import get_session
from .schemas import ProductoCreate, ProductoResponse
from .unit_of_work import ProductoUnitOfWork
from .service import ProductoService

router = APIRouter(prefix="/productos", tags=["Productos"])

def get_producto_service(session: Session = Depends(get_session)) -> ProductoService:
    return ProductoService(ProductoUnitOfWork(session))

@router.post("/", response_model=ProductoResponse, status_code=status.HTTP_201_CREATED)
def crear_producto(producto_in: ProductoCreate, service: ProductoService = Depends(get_producto_service)):
    return service.crear(producto_in)

@router.get("/", response_model=List[ProductoResponse], status_code=status.HTTP_200_OK)
def listar_productos(service: ProductoService = Depends(get_producto_service)):
    return service.listar_activos()