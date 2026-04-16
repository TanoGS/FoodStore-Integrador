from fastapi import HTTPException, status
from sqlmodel import Session, select

from .models import Usuario, Rol
from .schemas import UsuarioCreate, LoginRequest

def crear_usuario(usuario_in: UsuarioCreate, db: Session):
    # 1. Verificar si el email ya existe
    usuario_existente = db.exec(select(Usuario).where(Usuario.email == usuario_in.email)).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")
    
    # 2. Buscar el rol CLIENTE (y crearlo si no existe)
    rol_cliente = db.exec(select(Rol).where(Rol.nombre == "CLIENTE")).first()
    if not rol_cliente:
        rol_cliente = Rol(nombre="CLIENTE", descripcion="Usuario regular de la tienda")
        db.add(rol_cliente)
        db.commit()
        db.refresh(rol_cliente)

    # 3. Crear el nuevo usuario
    nuevo_usuario = Usuario(
        nombre=usuario_in.nombre,
        apellido=usuario_in.apellido,
        email=usuario_in.email,
        password_hash=usuario_in.password, # Guardado en plano temporalmente
        telefono=usuario_in.telefono,
        rol_id=rol_cliente.id
    )
    
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    return nuevo_usuario


def autenticar_usuario(login_data: LoginRequest, db: Session):
    # 1. Buscar al usuario por email
    usuario = db.exec(select(Usuario).where(Usuario.email == login_data.email)).first()
    
    # 2. Validar existencia y contraseña
    if not usuario or usuario.password_hash != login_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Credenciales inválidas"
        )
    
    # 3. Validar estado del usuario
    if not usuario.activo:
        raise HTTPException(status_code=400, detail="Usuario desactivado")
    
    # 4. Extraer el rol para el frontend
    rol = db.get(Rol, usuario.rol_id)
    
    return {
        **usuario.model_dump(),
        "rol_nombre": rol.nombre if rol else "CLIENTE"
    }