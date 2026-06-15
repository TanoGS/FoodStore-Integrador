from fastapi import HTTPException, status, Response
from datetime import datetime, timezone
from typing import List, Optional
from sqlmodel import Session, select 
from core.security import get_password_hash, verify_password, create_access_token
from .models import Usuario, Rol, UsuarioRol 
from .schemas import UsuarioCreate, UsuarioUpdate, UsuarioPublic
from .unit_of_work import UsuarioUnitOfWork
from sqlmodel import select
from sqlalchemy.orm import selectinload
from app.modules.usuario.models import Usuario


class UsuarioService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ====================================================================
    # 1. REGISTRO DE USUARIOS CON CLAVES NATURALES
    # ====================================================================
    def registrar_usuario(self, data: UsuarioCreate) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            if uow.usuarios.get_by_email(data.email):
                raise HTTPException(status_code=400, detail="El email ya está registrado")
            
            nuevo_usuario = Usuario(
                **data.model_dump(exclude={"password", "role_codigos"}),
                password=get_password_hash(data.password)
            )

            # Lógica de asignación de roles mediante Códigos (ej: "GESTOR_STOCK")
            codigos_a_asignar = data.role_codigos if data.role_codigos else ["CLIENTE"]
            
            for codigo in codigos_a_asignar:
                # Verificamos que el código de rol exista realmente en BD
                rol_existente = self._session.exec(select(Rol).where(Rol.codigo == codigo)).first()
                if not rol_existente:
                    raise HTTPException(status_code=400, detail=f"El rol con código '{codigo}' no existe")
                
                # Creamos la relación explícita hacia la tabla intermedia
                enlace = UsuarioRol(rol_codigo=rol_existente.codigo)
                nuevo_usuario.roles_enlaces.append(enlace)

            uow.usuarios.add(nuevo_usuario)
            
            self._session.flush()
            self._session.refresh(nuevo_usuario)
            
            return UsuarioPublic.model_validate(nuevo_usuario)

    # ====================================================================
    # 2. AUTENTICACIÓN STATELESS CON COOKIES HTTPONLY
    # ====================================================================
    def login(self, email: str, password_plana: str, response: Response) -> dict: #  Cambiamos retorno a dict
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = uow.usuarios.get_by_email(email)
            if not usuario or not verify_password(password_plana, usuario.password):
                raise HTTPException(status_code=401, detail="Credenciales incorrectas")
            
            if not usuario.activo:
                raise HTTPException(status_code=400, detail="Usuario inactivo")

            # Extraemos roles para el JWT
            roles_del_usuario = [enlace.rol_codigo for enlace in usuario.roles_enlaces]
            
            # Creamos el Token
            token = create_access_token(
                subject=str(usuario.id),
                roles=roles_del_usuario,
            )

            # Inyectamos el JWT en una cookie HttpOnly (no accesible desde JS)
            response.set_cookie(
                key="access_token",
                value=f"Bearer {token}",
                httponly=True,
                max_age=1800,       # 30 min — igual que ACCESS_TOKEN_EXPIRE_MINUTES
                samesite="lax",
                secure=False,       # True en producción con HTTPS
            )

            # Devolvemos también el token en el body para compatibilidad con Swagger
            return {
                "access_token": token,
                "token_type": "bearer",
                "usuario": UsuarioPublic.model_validate(usuario)
}

    def logout(self, response: Response) -> dict:
        #  DESTRUCCIÓN INMEDIATA DE LA SESIÓN 
        response.delete_cookie(
            key="access_token",
            httponly=True,
            samesite="lax"
        )
        return {"message": "Sesión cerrada de forma segura"}

    # ====================================================================
    # 3. ACTUALIZACIÓN Y AUDITORÍA DE USUARIOS (NUEVO)
    # ====================================================================
    def actualizar_usuario(self, usuario_id: int, data: UsuarioUpdate) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = self._session.get(Usuario, usuario_id)
            if not usuario:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
            # Extraemos solo los campos que el cliente envió para actualizar
            update_data = data.model_dump(exclude_unset=True)
            
            if "password" in update_data:
                update_data["password"] = get_password_hash(update_data["password"])
                
            for key, value in update_data.items():
                setattr(usuario, key, value)
                
            # Sello de auditoría automatizado
            usuario.actualizado_en = datetime.now(timezone.utc)
            
            uow.usuarios.add(usuario)
            self._session.flush()
            self._session.refresh(usuario)
            
            return UsuarioPublic.model_validate(usuario)

    # ====================================================================
    # 3.5. CAMBIAR CONTRASEÑA CON VERIFICACIÓN
    # ====================================================================
    def cambiar_password(self, usuario_id: int, password_actual: str, password_nueva: str) -> dict:
        """
        Permite cambiar la contraseña solo si la actual es correcta.
        """
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = self._session.get(Usuario, usuario_id)
            if not usuario:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
            # Verificar que la contraseña actual sea correcta
            if not verify_password(password_actual, usuario.password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="La contraseña actual es incorrecta"
                )
            
            # Actualizar contraseña
            usuario.password = get_password_hash(password_nueva)
            usuario.actualizado_en = datetime.now(timezone.utc)
            uow.usuarios.add(usuario)
            self._session.flush()
            
            return {"message": "Contraseña actualizada exitosamente"}

    # ====================================================================
    # 4. UTILIDADES Y SOFT DELETES (Sin Cambios)
    # ====================================================================
    def obtener_usuario_por_id(self, usuario_id: int) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = self._session.exec(
                select(Usuario)
                .where(Usuario.id == usuario_id)
                .options(selectinload(Usuario.roles_enlaces).selectinload(UsuarioRol.rol))
            ).first()
            if not usuario:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
            return UsuarioPublic.model_validate(usuario)

    def listar_usuarios(self, offset: int, limit: int, rol: Optional[str] = None):
        with UsuarioUnitOfWork(self._session) as uow:
            if rol:
                usuarios_orm = uow.usuarios.get_all_activos_por_rol(rol, offset, limit)
                total = uow.usuarios.count_activos_por_rol(rol)
            else:
                usuarios_orm = uow.usuarios.get_all_activos(offset, limit)
                total = uow.usuarios.count_activos()
            usuarios_pydantic = [UsuarioPublic.model_validate(u) for u in usuarios_orm]
            return {"data": usuarios_pydantic, "total": total}
        
    def eliminar_logicamente(self, usuario_id: int) -> dict:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = self._session.get(Usuario, usuario_id)
            if not usuario:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
            if usuario.eliminado_en is not None:
                raise HTTPException(status_code=400, detail="El usuario ya se encuentra eliminado")

            usuario.eliminado_en = datetime.now(timezone.utc)
            usuario.activo = False
            uow.usuarios.add(usuario)
            return {"message": f"Usuario {usuario_id} eliminado lógicamente con éxito"}

    def reactivar_usuario(self, usuario_id: int) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = self._session.get(Usuario, usuario_id)
            if not usuario:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
            if usuario.eliminado_en is None:
                raise HTTPException(status_code=400, detail="El usuario no está eliminado")

            usuario.eliminado_en = None
            usuario.activo = True
            uow.usuarios.add(usuario)
            self._session.flush()
            self._session.refresh(usuario)
            return UsuarioPublic.model_validate(usuario)
        
    def listar_para_gestion(self, offset: int, limit: int):
        with UsuarioUnitOfWork(self._session) as uow:
            usuarios_orm = uow.usuarios.get_all_incluyendo_eliminados(offset, limit)
            total = uow.usuarios.count_total()
            data = [UsuarioPublic.model_validate(u) for u in usuarios_orm]
            return {"data": data, "total": total}
        
    def obtener_todos_los_usuarios(self):
        """
        Obtiene todos los usuarios de la base de datos, 
        incluyendo la lista de roles asociados a cada uno.
        """
        with UsuarioUnitOfWork(self._session) as uow:
            statement = select(Usuario).options(
                selectinload(Usuario.roles_enlaces).selectinload(UsuarioRol.rol)
            )
            resultados = self._session.exec(statement).unique().all()
            return [UsuarioPublic.model_validate(u) for u in resultados]

    # ====================================================================
    # 5. ASIGNACIÓN DE ROLES
    # ====================================================================
    def asignar_roles(self, usuario_id: int, codigos: List[str], asignado_por_id: int | None = None) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = self._session.exec(
                select(Usuario)
                .where(Usuario.id == usuario_id)
                .options(selectinload(Usuario.roles_enlaces))
            ).first()
            if not usuario:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")

            for codigo in codigos:
                if not self._session.exec(select(Rol).where(Rol.codigo == codigo)).first():
                    raise HTTPException(status_code=400, detail=f"El rol '{codigo}' no existe")

            # Reemplazar roles (cascade delete-orphan borra los anteriores al flush)
            usuario.roles_enlaces.clear()
            self._session.flush()

            for codigo in codigos:
                enlace = UsuarioRol(rol_codigo=codigo, asignado_por_id=asignado_por_id)
                usuario.roles_enlaces.append(enlace)

            usuario.actualizado_en = datetime.now(timezone.utc)
            self._session.add(usuario)
            self._session.flush()
            self._session.refresh(usuario)
            return UsuarioPublic.model_validate(usuario)
