from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from core.database import get_session
from .schemas import UsuarioCreate, UsuarioResponse, LoginRequest

# Importamos nuestro nuevo archivo de servicios
from . import service 

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

@router.post("/registro", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registrar_usuario(usuario_in: UsuarioCreate, db: Session = Depends(get_session)):
    # Delegamos toda la lógica a la capa de servicio
    return service.crear_usuario(usuario_in, db)


@router.post("/login", response_model=UsuarioResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_session)):
    # Delegamos toda la lógica a la capa de servicio
    return service.autenticar_usuario(login_data, db)