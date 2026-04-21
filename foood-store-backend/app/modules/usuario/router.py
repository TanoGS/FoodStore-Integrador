from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from core.database import get_session
from .schemas import UsuarioCreate, UsuarioResponse, UsuarioUpdate
from .unit_of_work import UsuarioUnitOfWork
from .service import UsuarioService

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

def get_usuario_service(session: Session = Depends(get_session)) -> UsuarioService:
    return UsuarioService(UsuarioUnitOfWork(session))

@router.post("/registro", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registrar_nuevo_usuario(
    usuario_in: UsuarioCreate, 
    service: UsuarioService = Depends(get_usuario_service)
):
    return service.registrar_usuario(usuario_in)

@router.get("/", response_model=list[UsuarioResponse])
def listar_usuarios(skip: int = 0, limit: int = 100, service: UsuarioService = Depends(get_usuario_service)):
    return service.obtener_usuarios(skip, limit)

@router.get("/{id}", response_model=UsuarioResponse)
def obtener_usuario(id: int, service: UsuarioService = Depends(get_usuario_service)):
    return service.obtener_usuario_por_id(id)

@router.patch("/{id}", response_model=UsuarioResponse)
def actualizar_usuario(id: int, usuario_in: UsuarioUpdate, service: UsuarioService = Depends(get_usuario_service)):
    return service.actualizar_usuario(id, usuario_in)

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def eliminar_usuario(id: int, service: UsuarioService = Depends(get_usuario_service)):
    return service.eliminar_usuario(id)