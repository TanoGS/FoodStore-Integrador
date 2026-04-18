from fastapi import HTTPException, status
from .schemas import ProductoCreate
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