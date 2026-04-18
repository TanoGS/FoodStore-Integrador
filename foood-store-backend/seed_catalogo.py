from sqlmodel import Session, select
from core.database import engine

# Importamos nuestros modelos del Dominio 2
from app.modules.categoria.models import Categoria
from app.modules.ingrediente.models import Ingrediente
from app.modules.producto.models import Producto, ProductoCategoria, ProductoIngrediente

def sembrar_catalogo():
    with Session(engine) as db:
        print("🌱 Iniciando siembra del catálogo...")

        # --- 1. CREAR CATEGORÍAS ---
        categorias_data = [
            {"nombre": "Hamburguesas", "descripcion": "Las mejores hamburguesas caseras"},
            {"nombre": "Pizzas", "descripcion": "Pizzas a la piedra y masa madre"},
            {"nombre": "Acompañamientos", "descripcion": "Papas, aros de cebolla y más"},
            {"nombre": "Bebidas", "descripcion": "Gaseosas y cervezas"}
        ]
        
        categorias_db = {}
        for cat_data in categorias_data:
            cat = db.exec(select(Categoria).where(Categoria.nombre == cat_data["nombre"])).first()
            if not cat:
                cat = Categoria(**cat_data)
                db.add(cat)
                db.commit()
                db.refresh(cat)
            categorias_db[cat.nombre] = cat
        print("✅ Categorías listas.")

        # --- 2. CREAR INGREDIENTES ---
        ingredientes_data = [
            {"nombre": "Medallón de Carne 200g", "es_alergeno": False},
            {"nombre": "Pan de Papa", "es_alergeno": True}, # Contiene gluten/lácteos
            {"nombre": "Queso Cheddar", "es_alergeno": True}, # Lácteo
            {"nombre": "Panceta Crujiente", "es_alergeno": False},
            {"nombre": "Cebolla Crispy", "es_alergeno": False},
            {"nombre": "Salsa Especial", "es_alergeno": False},
            {"nombre": "Masa Madre", "es_alergeno": True}, # Gluten
            {"nombre": "Muzzarella", "es_alergeno": True}, # Lácteo
            {"nombre": "Salsa de Tomate", "es_alergeno": False}
        ]

        ingredientes_db = {}
        for ing_data in ingredientes_data:
            ing = db.exec(select(Ingrediente).where(Ingrediente.nombre == ing_data["nombre"])).first()
            if not ing:
                ing = Ingrediente(**ing_data)
                db.add(ing)
                db.commit()
                db.refresh(ing)
            ingredientes_db[ing.nombre] = ing
        print("✅ Ingredientes listos.")

        # --- 3. CREAR PRODUCTOS Y RELACIONES ---
        productos_data = [
            {
                "nombre": "Doble Bacon Cheeseburger",
                "descripcion": "Doble medallón de carne, cuádruple cheddar, panceta y salsa especial.",
                "precio_base": 12500.0,
                "es_personalizable": True,
                "stock_disponible": 50,
                "categoria": "Hamburguesas",
                "ingredientes": [
                    ("Pan de Papa", False, 0), # No removible, sin precio extra
                    ("Medallón de Carne 200g", False, 0),
                    ("Queso Cheddar", True, 1000.0), # Removible, si agrega extra cuesta 1000
                    ("Panceta Crujiente", True, 1500.0),
                    ("Salsa Especial", True, 0)
                ]
            },
            {
                "nombre": "Pizza Margarita",
                "descripcion": "Clásica pizza italiana con salsa de tomate natural y muzzarella fior di latte.",
                "precio_base": 15000.0,
                "es_personalizable": True,
                "stock_disponible": 30,
                "categoria": "Pizzas",
                "ingredientes": [
                    ("Masa Madre", False, 0),
                    ("Salsa de Tomate", False, 0),
                    ("Muzzarella", True, 2000.0)
                ]
            }
        ]

        for prod_data in productos_data:
            # Verificar si existe
            prod = db.exec(select(Producto).where(Producto.nombre == prod_data["nombre"])).first()
            if not prod:
                # 3.1 Crear Producto
                prod = Producto(
                    nombre=prod_data["nombre"],
                    descripcion=prod_data["descripcion"],
                    precio_base=prod_data["precio_base"],
                    es_personalizable=prod_data["es_personalizable"],
                    stock_disponible=prod_data["stock_disponible"]
                )
                db.add(prod)
                db.commit()
                db.refresh(prod)

                # 3.2 Asociar Categoría (Muchos a Muchos)
                cat = categorias_db[prod_data["categoria"]]
                rel_cat = ProductoCategoria(producto_id=prod.id, categoria_id=cat.id)
                db.add(rel_cat)

                # 3.3 Asociar Ingredientes (Muchos a Muchos con atributos extra)
                for ing_nombre, es_removible, precio_extra in prod_data["ingredientes"]:
                    ing = ingredientes_db[ing_nombre]
                    rel_ing = ProductoIngrediente(
                        producto_id=prod.id,
                        ingrediente_id=ing.id,
                        es_removible=es_removible,
                        precio_adicional=precio_extra
                    )
                    db.add(rel_ing)
                
                db.commit()
                print(f"🍔 Producto '{prod.nombre}' creado con sus relaciones.")
            else:
                print(f"⚠️ El producto '{prod.nombre}' ya existía.")

        print("🎉 ¡Catálogo sembrado exitosamente!")

if __name__ == "__main__":
    sembrar_catalogo()