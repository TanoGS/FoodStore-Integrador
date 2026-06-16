import os
import subprocess
from datetime import datetime

from sqlmodel import Session, SQLModel
from sqlalchemy import text
from core.database import engine
from core.security import get_password_hash

from app.modules.catalogo.categoria.models import Categoria
from app.modules.catalogo.ingrediente.models import Ingrediente, UnidadMedida
from app.modules.catalogo.producto.models import Producto
from app.modules.catalogo.shared_models import ProductoCategoria, ProductoIngrediente
from app.modules.usuario.models import Usuario, Rol, UsuarioRol, Permiso, RolPermiso
from app.modules.direccion.models import DireccionEntrega
from app.modules.pedido.models import Pedido, DetallePedido, HistorialEstadoPedido, EstadoPedido, FormaPago, TipoEntrega
from app.modules.pagos.models import Pago
from app.modules.imagenes.models import Imagen

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
    # Imágenes
    ("GESTIONAR_IMAGENES",    "Cargar, listar, obtener y eliminar imágenes del catálogo"),
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
        "GESTIONAR_IMAGENES",
    ],
    "GESTOR_PEDIDOS": [
        "VER_CATALOGO",
        "GESTIONAR_PEDIDOS",
        "VER_PEDIDOS_PROPIOS",
    ],
    "CAJERO": [
        "VER_CATALOGO",
        "CREAR_PEDIDO",
        "GESTIONAR_PEDIDOS",
        "VER_PEDIDOS_PROPIOS",
        "VER_PERFIL_PROPIO",
    ],
    "COCINA": [
        "VER_CATALOGO",
        "GESTIONAR_PEDIDOS",
        "VER_PERFIL_PROPIO",
    ],
}


def inicializar_sistema():
    print(" Detectando modelos y recreando la estructura completa de la BD...")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # ====================================================================
        # 1. ROLES
        # ====================================================================
        print(" Sembrando Roles...")
        roles_maestros = [
            Rol(codigo="ADMIN",          nombre="Administrador",    descripcion="Control total y auditoría global del sistema"),
            Rol(codigo="CLIENTE",        nombre="Cliente Tienda",   descripcion="Usuario final consumidor del catálogo"),
            Rol(codigo="GESTOR_STOCK",   nombre="Gestor de Stock",  descripcion="Administrador del inventario e ingredientes"),
            Rol(codigo="GESTOR_PEDIDOS", nombre="Gestor de Pedidos",descripcion="Operador encargado de la máquina de estados de las órdenes"),
            Rol(codigo="CAJERO",         nombre="Cajero",           descripcion="Toma pedidos en mostrador, confirma pagos y gestiona el ciclo inicial del pedido"),
            Rol(codigo="COCINA",         nombre="Cocina",           descripcion="Responsable de preparar pedidos y marcarlos como listos/en camino"),
        ]
        for rol in roles_maestros:
            session.add(rol)
        session.commit()

        # ====================================================================
        # 2. PERMISOS
        # ====================================================================
        print(" Sembrando Permisos...")
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

        # ====================================================================
        # 3. USUARIOS DE PRUEBA
        # ====================================================================
        print(" Registrando Super Usuario Administrador inicial...")
        admin_user = Usuario(
            email="admin@foodstore.com",
            nombre="John",
            apellido="Rambo",
            cel="2615551234",
            password=get_password_hash("admin123"),
            activo=True,
            creado_en=datetime.utcnow()
        )
        session.add(admin_user)
        session.flush()

        print(" Vinculando Admin → Rol ADMIN...")
        session.add(UsuarioRol(
            usuario_id=admin_user.id,
            rol_codigo="ADMIN",
            asignado_por_id=admin_user.id,
            expires_at=None,
        ))
        session.commit()

        print(" Registrando usuario Cajero de prueba...")
        cajero_user = Usuario(
            email="cajero@foodstore.com",
            nombre="Cajero",
            apellido="FoodStore",
            cel="2615555678",
            password=get_password_hash("cajero123"),
            activo=True,
            creado_en=datetime.utcnow()
        )
        session.add(cajero_user)
        session.flush()

        print(" Vinculando Cajero → Rol CAJERO...")
        session.add(UsuarioRol(
            usuario_id=cajero_user.id,
            rol_codigo="CAJERO",
            asignado_por_id=admin_user.id,
            expires_at=None,
        ))
        session.commit()

        print(" Registrando usuario Cliente de prueba...")
        cliente_user = Usuario(
            email="pepe@gmail.com",
            nombre="Pepe",
            apellido="García",
            cel="2615559999",
            password=get_password_hash("pepe123"),
            activo=True,
            creado_en=datetime.utcnow()
        )
        session.add(cliente_user)
        session.flush()

        print(" Vinculando Cliente → Rol CLIENTE...")
        session.add(UsuarioRol(
            usuario_id=cliente_user.id,
            rol_codigo="CLIENTE",
            asignado_por_id=admin_user.id,
            expires_at=None,
        ))
        session.commit()

        # ====================================================================
        # 3b. USUARIO: GESTOR DE STOCK
        # ====================================================================
        print(" Registrando usuario Gestor de Stock de prueba...")
        stock_user = Usuario(
            email="stock@foodstore.com",
            nombre="Arnoldo",
            apellido="Schwarzenegger",
            cel="2615551111",
            password=get_password_hash("stock123"),
            activo=True,
            creado_en=datetime.utcnow()
        )
        session.add(stock_user)
        session.flush()

        print(" Vinculando Stock → Rol GESTOR_STOCK...")
        session.add(UsuarioRol(
            usuario_id=stock_user.id,
            rol_codigo="GESTOR_STOCK",
            asignado_por_id=admin_user.id,
            expires_at=None,
        ))
        session.commit()

        # ====================================================================
        # 3c. USUARIO: GESTOR DE PEDIDOS
        # ====================================================================
        print(" Registrando usuario Gestor de Pedidos de prueba...")
        pedidos_user = Usuario(
            email="pedidos@foodstore.com",
            nombre="John",
            apellido="Wick",
            cel="2615552222",
            password=get_password_hash("pedidos123"),
            activo=True,
            creado_en=datetime.utcnow()
        )
        session.add(pedidos_user)
        session.flush()

        print(" Vinculando Pedidos → Rol GESTOR_PEDIDOS...")
        session.add(UsuarioRol(
            usuario_id=pedidos_user.id,
            rol_codigo="GESTOR_PEDIDOS",
            asignado_por_id=admin_user.id,
            expires_at=None,
        ))
        session.commit()

        # ====================================================================
        # 3d. USUARIO: COCINA
        # ====================================================================
        print(" Registrando usuario Cocina de prueba...")
        cocina_user = Usuario(
            email="cocina@foodstore.com",
            nombre="Connor",
            apellido="MacLeod",
            cel="2615553333",
            password=get_password_hash("cocina123"),
            activo=True,
            creado_en=datetime.utcnow()
        )
        session.add(cocina_user)
        session.flush()

        print(" Vinculando Cocina → Rol COCINA...")
        session.add(UsuarioRol(
            usuario_id=cocina_user.id,
            rol_codigo="COCINA",
            asignado_por_id=admin_user.id,
            expires_at=None,
        ))
        session.commit()

    print("\n=======================================================================")
    print("¡Base de Datos FoodStore inicializada con éxito! ")
    print("=======================================================================")
    print("Roles seedeados: ADMIN | CLIENTE | GESTOR_STOCK | GESTOR_PEDIDOS | CAJERO | COCINA")
    print(f"Permisos seedeados: {len(PERMISOS)}")
    print("=======================================================================")
    print("USUARIOS DE PRUEBA (uno por cada rol):")
    print("  ADMIN:          admin@foodstore.com    | Clave: admin123")
    print("  CLIENTE:        pepe@gmail.com        | Clave: pepe123")
    print("  GESTOR_STOCK:   stock@foodstore.com    | Clave: stock123")
    print("  GESTOR_PEDIDOS: pedidos@foodstore.com | Clave: pedidos123")
    print("  CAJERO:         cajero@foodstore.com   | Clave: cajero123")
    print("  COCINA:         cocina@foodstore.com   | Clave: cocina123")
    print("=======================================================================")
    print("Todas las tablas del sistema fueron creadas vacías (sin datos de catálogo).")

    # Sincronizar Alembic para que no intente volver a crear las tablas ya existentes
    print(" Sincronizando versión de Alembic (alembic stamp head)...")
    try:
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        subprocess.run(
            ["alembic", "stamp", "head"],
            cwd=backend_dir,
            check=True,
        )
        print(" Versión de Alembic registrada correctamente.")
    except Exception as e:
        print(f"  No se pudo ejecutar 'alembic stamp head' automáticamente: {e}")
        print("  Ejecutá manualmente: alembic stamp head")
    print("=======================================================================")


if __name__ == "__main__":
    inicializar_sistema()
