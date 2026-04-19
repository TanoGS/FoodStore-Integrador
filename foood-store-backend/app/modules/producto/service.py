from datetime import datetime, timezone
from fastapi import HTTPException, status
from .schemas import ProductoCreate, ProductoUpdate
from .models import Producto
from .unit_of_work import ProductoUnitOfWork

class ProductoService:
    def __init__(self, uow: ProductoUnitOfWork):
        self.uow = uow

    def crear(self, data: ProductoCreate) -> Producto:
        # 1. Validar nombre único
        if self.uow.productos.get_by_nombre(data.nombre):
            raise HTTPException(status_code=400, detail="Ya existe un producto con este nombre")

        try:
            # 2. Separar los IDs de categoría de los datos del producto
            categoria_ids = data.categoria_ids
            prod_dict = data.model_dump(exclude={"categoria_ids"})

            # 3. Crear el producto
            nuevo_producto = Producto(**prod_dict)
            self.uow.productos.add(nuevo_producto)
            self.uow.commit() # Primer commit para obtener el ID real
            self.uow.session.refresh(nuevo_producto)

            # 4. Asociar categorías (Si el front envió alguna)
            if categoria_ids:
                self.uow.productos.asociar_categorias(nuevo_producto.id, categoria_ids)
                self.uow.commit() # Segundo commit para guardar las relaciones

            return nuevo_producto

        except Exception as e:
            self.uow.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    def listar_activos(self) -> list[Producto]:
        return self.uow.productos.get_all_activos()
    
    def actualizar(self, id: int, data: ProductoUpdate) -> Producto:
        # 1. Buscar el producto
        producto = self.uow.productos.get_by_id(id)
        if not producto or producto.eliminado_en is not None:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        # 2. Validar que el nuevo nombre no colisione
        if data.nombre and data.nombre != producto.nombre:
            if self.uow.productos.get_by_nombre(data.nombre):
                raise HTTPException(status_code=400, detail="Ya existe otro producto con este nombre")

        try:
            # 3. Actualizar datos base (excluyendo la lista de categorías)
            update_data = data.model_dump(exclude_unset=True, exclude={"categoria_ids"})
            for key, value in update_data.items():
                setattr(producto, key, value)

            # 4. Actualizar relaciones si enviaron la lista
            if data.categoria_ids is not None:
                self.uow.productos.limpiar_categorias(id)
                self.uow.productos.asociar_categorias(id, data.categoria_ids)

            # 5. Guardar todo
            self.uow.commit()
            self.uow.session.refresh(producto)
            return producto
        except Exception as e:
            self.uow.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    def eliminar_logicamente(self, id: int):
        producto = self.uow.productos.get_by_id(id)
        if not producto or producto.eliminado_en is not None:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        try:
            # Soft Delete y desactivación
            producto.eliminado_en = datetime.now(timezone.utc)
            producto.activo = False 
            self.uow.commit()
            return {"message": f"Producto '{producto.nombre}' eliminado correctamente."}
        except Exception as e:
            self.uow.rollback()
            raise HTTPException(status_code=500, detail=str(e))