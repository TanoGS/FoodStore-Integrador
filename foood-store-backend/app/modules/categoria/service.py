from fastapi import HTTPException, status
from datetime import datetime, timezone
from .schemas import CategoriaCreate, CategoriaUpdate
from .models import Categoria
from .unit_of_work import CategoriaUnitOfWork

class CategoriaService:
    def __init__(self, uow: CategoriaUnitOfWork):
        self.uow = uow

    def crear(self, data: CategoriaCreate) -> Categoria:
        if data.padre_id == 0:
            data.padre_id = None
        # Regla 1: El nombre debe ser único
        if self.uow.categorias.get_by_nombre(data.nombre):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Ya existe una categoría con este nombre."
            )

        # Regla 2: Si tiene padre_id, el padre debe existir y estar activo
        if data.padre_id:
            padre = self.uow.categorias.get_by_id(data.padre_id)
            if not padre or padre.eliminado_en is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="La categoría padre indicada no existe o está eliminada."
                )

        # Persistencia atómica
        try:
            nueva_categoria = Categoria(**data.model_dump())
            self.uow.categorias.add(nueva_categoria)
            self.uow.commit()
            self.uow.session.refresh(nueva_categoria)
            return nueva_categoria
        except Exception as e:
            self.uow.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    def listar_activas(self) -> list[Categoria]:
        return self.uow.categorias.get_all_activas()
    
    def actualizar(self, id: int, data: CategoriaUpdate) -> Categoria:
        # 1. Buscar la categoría a modificar
        categoria = self.uow.categorias.get_by_id(id)
        if not categoria or categoria.eliminado_en is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Categoría no encontrada."
            )

        # 2. Si están intentando cambiar el nombre, validar que no exista ya
        if data.nombre and data.nombre != categoria.nombre:
            if self.uow.categorias.get_by_nombre(data.nombre):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Ya existe otra categoría con este nombre."
                )

        # 3. Si están asignando un nuevo padre
        if data.padre_id is not None:
            # Evitar que una categoría sea su propio padre
            if data.padre_id == id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Una categoría no puede ser subcategoría de sí misma."
                )
            # Validar que el padre exista
            padre = self.uow.categorias.get_by_id(data.padre_id)
            if not padre or padre.eliminado_en is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="La categoría padre indicada no existe o está eliminada."
                )

        # 4. Actualizar dinámicamente solo los campos que fueron enviados
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(categoria, key, value)

        # 5. Persistir los cambios
        try:
            self.uow.commit()
            self.uow.session.refresh(categoria)
            return categoria
        except Exception as e:
            self.uow.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    def eliminar_logicamente(self, id: int):
        categoria = self.uow.categorias.get_by_id(id)
        if not categoria or categoria.eliminado_en is not None:
            raise HTTPException(status_code=404, detail="Categoría no encontrada.")

        try:
            # Aplicamos Soft Delete
            categoria.eliminado_en = datetime.now(timezone.utc)
            self.uow.commit()
            return {"message": f"Categoría '{categoria.nombre}' eliminada correctamente."}
        except Exception as e:
            self.uow.rollback()
            raise HTTPException(status_code=500, detail=str(e))