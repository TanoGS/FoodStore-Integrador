from datetime import datetime, timezone
from fastapi import HTTPException, status
from .schemas import ProductoCreate, ProductoUpdate
from .models import Producto

class ProductoService:
    def __init__(self, uow):
        self.uow = uow

    def crear(self, data: ProductoCreate) -> Producto:
        # 1. Validar nombre único
        if self.uow.productos.get_by_nombre(data.nombre):
            raise HTTPException(status_code=400, detail="Ya existe un producto con este nombre")

        # 2. Crear instancia base
        prod_dict = data.model_dump(exclude={"categoria_ids"})
        nuevo_producto = Producto(**prod_dict)

        # 3. Vincular Categorías (La Magia de Relationship)
        if data.categoria_ids:
            for cat_id in data.categoria_ids:
                categoria = self.uow.categorias.get_by_id(cat_id)
                if not categoria or categoria.eliminado_en:
                    raise HTTPException(status_code=400, detail=f"Categoría {cat_id} no válida")
                # Al agregar a la lista, SQLModel hará el insert en la intermedia solo
                nuevo_producto.categorias.append(categoria)

        try:
            self.uow.productos.add(nuevo_producto)
            self.uow.commit()
            self.uow.session.refresh(nuevo_producto)
            return nuevo_producto
        except Exception as e:
            self.uow.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        
    def listar_activos(self):
        """Devuelve todos los productos que están activos y no eliminados."""
        return self.uow.productos.get_all_activos()

    def obtener_por_id(self, id: int):
        """Busca un producto por su ID."""
        producto = self.uow.productos.get_by_id(id)
        if not producto or producto.eliminado_en is not None:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return producto

    def actualizar(self, id: int, data: ProductoUpdate):
        producto = self.uow.productos.get_by_id(id)
        if not producto: raise HTTPException(status_code=404)

        update_data = data.model_dump(exclude_unset=True, exclude={"categoria_ids"})
        for key, value in update_data.items():
            setattr(producto, key, value)

        # Actualizar categorías si vienen en el body
        if data.categoria_ids is not None:
            # Vaciamos las actuales y cargamos las nuevas
            producto.categorias = [] 
            for cat_id in data.categoria_ids:
                cat = self.uow.categorias.get_by_id(cat_id)
                if cat: producto.categorias.append(cat)

        self.uow.commit()
        self.uow.session.refresh(producto)
        return producto