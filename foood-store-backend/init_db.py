from sqlmodel import Session, SQLModel
from sqlalchemy import text
from core.database import engine
from core.security import get_password_hash
from datetime import datetime

from app.modules.catalogo.categoria.models import Categoria
from app.modules.catalogo.ingrediente.models import Ingrediente
from app.modules.catalogo.producto.models import Producto
from app.modules.catalogo.shared_models import ProductoCategoria, ProductoIngrediente
from app.modules.usuario.models import Usuario, Rol, UsuarioRol, Permiso, RolPermiso
from app.modules.pedido.models import Pedido, DetallePedido, HistorialEstadoPedido
from app.modules.direccion.models import DireccionEntrega

# ---------------------------------------------------------------------------
# Catálogo de permisos: (nombre, descripción)
# ---------------------------------------------------------------------------
PERMISOS = [
    # Catálogo
    ("VER_CATALOGO",          "Ver productos, categorías e ingredientes"),
    ("GESTIONAR_PRODUCTOS",   "Crear, editar y eliminar productos"),
    ("GESTIONAR_CATEGORIAS",  "Crear, editar y eliminar categorías"),
    ("GESTIONAR_INGREDIENTES","Crear, editar y eliminar ingredientes"),
    # Pedidos
    ("CREAR_PEDIDO",          "Realizar un pedido nuevo"),
    ("VER_PEDIDOS_PROPIOS",   "Ver el historial de pedidos propios"),
    ("GESTIONAR_PEDIDOS",     "Ver y gestionar todos los pedidos del sistema"),
    # Usuarios y perfil
    ("VER_PERFIL_PROPIO",     "Acceder a /me y datos personales"),
    ("GESTIONAR_USUARIOS",    "Listar, editar y administrar usuarios"),
    # Direcciones
    ("GESTIONAR_DIRECCIONES", "CRUD de direcciones de entrega propias"),
]

# ---------------------------------------------------------------------------
# Asignación permisos → roles
# ---------------------------------------------------------------------------
PERMISOS_POR_ROL = {
    "ADMIN": [p[0] for p in PERMISOS],   # todos los permisos
    "CLIENTE": [
        "VER_CATALOGO",
        "CREAR_PEDIDO",
        "VER_PEDIDOS_PROPIOS",
        "VER_PERFIL_PROPIO",
        "GESTIONAR_DIRECCIONES",
    ],
    "GESTOR_STOCK": [
        "VER_CATALOGO",
        "GESTIONAR_PRODUCTOS",
        "GESTIONAR_CATEGORIAS",
        "GESTIONAR_INGREDIENTES",
    ],
    "GESTOR_PEDIDOS": [
        "VER_CATALOGO",
        "GESTIONAR_PEDIDOS",
        "VER_PEDIDOS_PROPIOS",
    ],
}

def inicializar_sistema():
    print("⏳ Detectando modelos y recreando la estructura completa de la BD...")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        print("🌱 Sembrando Roles...")
        roles_maestros = [
            Rol(codigo="ADMIN",          nombre="Administrador",    descripcion="Control total y auditoría global del sistema"),
            Rol(codigo="CLIENTE",        nombre="Cliente Tienda",   descripcion="Usuario final consumidor del catálogo"),
            Rol(codigo="GESTOR_STOCK",   nombre="Gestor de Stock",  descripcion="Administrador del inventario e ingredientes"),
            Rol(codigo="GESTOR_PEDIDOS", nombre="Gestor de Pedidos",descripcion="Operador encargado de la máquina de estados de las órdenes"),
        ]
        for rol in roles_maestros:
            session.add(rol)
        session.commit()

        print("🔑 Sembrando Permisos...")
        permisos_map: dict[str, Permiso] = {}
        for nombre, descripcion in PERMISOS:
            p = Permiso(nombre=nombre, descripcion=descripcion)
            session.add(p)
            permisos_map[nombre] = p
        session.flush()  # genera los IDs de los permisos

        print("🔗 Vinculando Permisos → Roles...")
        for rol_codigo, nombres in PERMISOS_POR_ROL.items():
            for nombre in nombres:
                session.add(RolPermiso(
                    rol_codigo=rol_codigo,
                    permiso_id=permisos_map[nombre].id,
                ))
        session.commit()

        print("👤 Registrando Super Usuario Administrador inicial...")
        admin_user = Usuario(
            email="admin@foodstore.com",
            nombre="Admin",
            apellido="FoodStore",

            cel="2615551234",
            password=get_password_hash("admin123"),
            activo=True,
            creado_en=datetime.utcnow()
        )
        session.add(admin_user)
        session.flush()

        print("🔗 Vinculando Admin → Rol ADMIN...")
        session.add(UsuarioRol(
            usuario_id=admin_user.id,
            rol_codigo="ADMIN",
            asignado_por_id=admin_user.id,
            expires_at=None,
        ))
        session.commit()

    print("\n=======================================================================")
    print("¡Base de Datos FoodStore inicializada con éxito! 🚀")
    print("Roles: ADMIN | CLIENTE | GESTOR_STOCK | GESTOR_PEDIDOS")
    print(f"Permisos seeded: {len(PERMISOS)}")
    print("Usuario Admin: admin@foodstore.com | Clave: admin123")
    print("=======================================================================")

if __name__ == "__main__":
    inicializar_sistema()