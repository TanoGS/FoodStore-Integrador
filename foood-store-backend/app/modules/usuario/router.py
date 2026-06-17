from fastapi import APIRouter, Depends, status, Response, Query, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from typing import List, Optional

from core.database import get_session
from core.security import get_current_user_token, RoleChecker, TokenData
from .schemas import UsuarioCreate, UsuarioPublic, UsuarioList, UsuarioUpdate, AsignarRolesInput
from .service import UsuarioService

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

# Dependencias de seguridad reutilizables
requiere_auth  = Depends(get_current_user_token)
requiere_admin = RoleChecker(["ADMIN"])

def get_usuario_service(session: Session = Depends(get_session)) -> UsuarioService:
    return UsuarioService(session)

# ==============================================================================
# 1. AUTENTICACIÓN Y REGISTRO
# ==============================================================================

@router.post("/registro", response_model=UsuarioPublic, status_code=status.HTTP_201_CREATED)
def registrar(data: UsuarioCreate, svc: UsuarioService = Depends(get_usuario_service)):
    return svc.registrar_usuario(data)

# 1. Cambiamos el response_model a 'dict' o lo quitamos para que sea flexible
@router.post("/login") 
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    svc: UsuarioService = Depends(get_usuario_service)
):
    # Asegúrate de que este método en tu service.py devuelva:
    # { "access_token": "...", "token_type": "bearer", "email": "...", "nombre": "...", ... }
    return svc.login(form_data.username, form_data.password, response)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    svc: UsuarioService = Depends(get_usuario_service),
):
    raw_refresh = request.cookies.get("refresh_token")
    svc.logout(response, raw_refresh=raw_refresh)


@router.post("/refresh", status_code=status.HTTP_200_OK)
def refresh_token(
    request: Request,
    response: Response,
    svc: UsuarioService = Depends(get_usuario_service),
):
    """
    Rota el par access_token / refresh_token.
    El refresh_token debe llegar en la cookie HttpOnly ``refresh_token``.
    """
    raw_refresh = request.cookies.get("refresh_token")
    if not raw_refresh:
        raise HTTPException(status_code=401, detail="refresh_token no encontrado en cookies.")
    return svc.refresh_access_token(raw_refresh, response)

# ==============================================================================
# 2. PERFIL PROPIO
# ==============================================================================

@router.get("/me", response_model=UsuarioPublic, summary="Obtener perfil propio")
def obtener_mi_perfil(
    current_user: TokenData = requiere_auth,
    svc: UsuarioService = Depends(get_usuario_service)
):
    """Devuelve los datos del usuario actualmente logueado según su Token."""
    return svc.obtener_usuario_por_id(int(current_user.id))


@router.patch("/me", response_model=UsuarioPublic, summary="Actualizar perfil propio")
def actualizar_mi_perfil(
    data: UsuarioUpdate,
    current_user: TokenData = requiere_auth,
    svc: UsuarioService = Depends(get_usuario_service)
):
    """Permite al usuario logueado actualizar su propia información."""
    return svc.actualizar_usuario(int(current_user.id), data)


@router.post("/me/cambiar-password", summary="Cambiar contraseña con verificación")
def cambiar_password(
    body: dict,
    current_user: TokenData = requiere_auth,
    svc: UsuarioService = Depends(get_usuario_service)
):
    """
    Permite al usuario cambiar su contraseña.
    Requiere la contraseña actual para verificar identidad.
    """
    password_actual = body.get("password_actual")
    password_nueva = body.get("password_nueva")
    
    if not password_actual or not password_nueva:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requiere password_actual y password_nueva"
        )
    
    if len(password_nueva) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe tener al menos 6 caracteres"
        )
    
    return svc.cambiar_password(
        usuario_id=int(current_user.id),
        password_actual=password_actual,
        password_nueva=password_nueva
    )


# ==============================================================================
# 3. GESTIÓN ADMINISTRATIVA (Solo ADMIN)
# ==============================================================================

@router.get("/", response_model=UsuarioList, dependencies=[Depends(requiere_admin)])
def listar_activos(
    offset: int = 0,
    limit: int = 20,
    rol: Optional[str] = Query(default=None, description="Filtrar por código de rol (ej: CLIENTE, ADMIN)"),
    svc: UsuarioService = Depends(get_usuario_service),
):
    """Lista usuarios activos con paginación. Acepta filtro opcional por código de rol. Solo ADMIN."""
    return svc.listar_usuarios(offset, limit, rol)


@router.get("/gestion", response_model=List[UsuarioPublic], tags=["Usuarios - Gestión"], dependencies=[Depends(requiere_admin)])
def listar_todos_los_usuarios(svc: UsuarioService = Depends(get_usuario_service)):
    """Lista TODOS los usuarios (activos e inactivos). Ideal para el Panel de Control."""
    return svc.obtener_todos_los_usuarios()


@router.get("/{id}", response_model=UsuarioPublic, dependencies=[Depends(requiere_admin)])
def obtener_usuario_por_id(id: int, svc: UsuarioService = Depends(get_usuario_service)):
    """Obtiene un usuario por ID incluyendo sus roles. Solo ADMIN."""
    return svc.obtener_usuario_por_id(id)


@router.delete("/{id}", status_code=status.HTTP_200_OK, summary="Eliminar usuario (Soft Delete)", dependencies=[Depends(requiere_admin)])
def eliminar_usuario(id: int, svc: UsuarioService = Depends(get_usuario_service)):
    """Da de baja a un usuario. Operación exclusiva de administradores."""
    return svc.eliminar_logicamente(id)


@router.patch("/{id}/reactivar", response_model=UsuarioPublic, status_code=status.HTTP_200_OK, summary="Reactivar usuario eliminado", dependencies=[Depends(requiere_admin)])
def reactivar_usuario(id: int, svc: UsuarioService = Depends(get_usuario_service)):
    """Reactiva a un usuario dado de baja. Operación exclusiva de administradores."""
    return svc.reactivar_usuario(id)


@router.patch("/{id}/roles", response_model=UsuarioPublic, summary="Asignar roles a usuario")
def asignar_roles(
    id: int,
    data: AsignarRolesInput,
    token: TokenData = Depends(requiere_admin),
    svc: UsuarioService = Depends(get_usuario_service),
):
    """Reemplaza completamente los roles de un usuario por los indicados. Solo ADMIN."""
    return svc.asignar_roles(id, data.role_codigos, asignado_por_id=int(token.id))


@router.patch("/{id}", response_model=UsuarioPublic, summary="Actualizar usuario (Admin)", dependencies=[Depends(requiere_admin)])
def actualizar_usuario_admin(
    id: int,
    data: UsuarioUpdate,
    svc: UsuarioService = Depends(get_usuario_service),
):
    """Actualiza datos de cualquier usuario. Solo ADMIN."""
    return svc.actualizar_usuario(id, data)
