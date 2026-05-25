from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from core.db import get_session
from core.security import verify_password, create_access_token
from app.modules.usuario.service import UsuarioService

router = APIRouter(tags=["Auth"])

@router.post("/login")
def login(db: Session = Depends(get_session), form_data: OAuth2PasswordRequestForm = Depends()):
    # OAuth2PasswordRequestForm guarda el email en el campo "username"
    usuario = UsuarioService.obtener_por_email(db, email=form_data.username)
    
    if not usuario or not verify_password(form_data.password, usuario.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not usuario.activo:
        raise HTTPException(status_code=400, detail="Usuario inactivo")

    # Creamos el token
    access_token = create_access_token(subject=usuario.id, roles=usuario.rol)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": usuario.id,
            "email": usuario.email,
            "nombre": usuario.nombre,
            "rol": usuario.rol
        }
    }