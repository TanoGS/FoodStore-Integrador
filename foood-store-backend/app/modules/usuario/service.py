from typing import List

from fastapi import HTTPException, status
from .schemas import UsuarioCreate, UsuarioUpdate
from .models import Usuario
from .unit_of_work import UsuarioUnitOfWork
from datetime import datetime, timezone

class UsuarioService:
    def __init__(self, uow: UsuarioUnitOfWork):
        self.uow = uow

    def registrar_usuario(self, data: UsuarioCreate) -> Usuario:
        if self.uow.usuarios.get_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="El email ya está registrado en el sistema."
            )

        try:
            # Pasa todos los datos directamente, incluyendo el password en plano
            nuevo_usuario = Usuario(**data.model_dump())
            self.uow.usuarios.add(nuevo_usuario)
            self.uow.commit()
            self.uow.session.refresh(nuevo_usuario)
            
            return nuevo_usuario
        except Exception as e:
            self.uow.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        
    def obtener_usuarios(self, skip: int = 0, limit: int = 100) -> List[Usuario]:
        return self.uow.usuarios.get_all(skip=skip, limit=limit)

    def obtener_usuario_por_id(self, id: int) -> Usuario:
        usuario = self.uow.usuarios.get_by_id(id)
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        return usuario

    def actualizar_usuario(self, id: int, data: UsuarioUpdate) -> Usuario:
        usuario = self.obtener_usuario_por_id(id) # Validación reutilizada
        
        # Extraemos solo los campos que fueron enviados en la petición
        update_data = data.model_dump(exclude_unset=True)
        
        try:
            for key, value in update_data.items():
                setattr(usuario, key, value)
                
            self.uow.commit()
            self.uow.session.refresh(usuario)
            return usuario
        except Exception as e:
            self.uow.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    def eliminar_usuario(self, id: int):
        usuario = self.obtener_usuario_por_id(id)
        
        try:
            # Borrado lógico
            usuario.activo = False
            usuario.eliminado_en = datetime.now(timezone.utc)
            
            self.uow.commit()
            return {"mensaje": "Usuario eliminado correctamente (Soft Delete)"}
        except Exception as e:
            self.uow.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        
    def listar_activos(self, skip: int, limit: int) -> List[Usuario]:
        return self.uow.usuarios.get_activos(skip, limit)

    def listar_eliminados(self, skip: int, limit: int) -> List[Usuario]:
        return self.uow.usuarios.get_eliminados(skip, limit)