from sqlmodel import Session, SQLModel
from sqlalchemy import text
from core.database import engine
from core.security import get_password_hash
from datetime import datetime

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

        # ====================================================================
        # 4. CATEGORÍAS (4)
        # ====================================================================
        print(" Sembrando Categorías...")
        cat_pizzas    = Categoria(nombre="Pizzas",    descripcion="Pizzas artesanales elaboradas con masa madre", activo=True)
        cat_bebidas   = Categoria(nombre="Bebidas",   descripcion="Gaseosas y aguas", activo=True)
        cat_entradas  = Categoria(nombre="Entradas",   descripcion="Para compartir antes de la comida principal", activo=True)
        cat_postres   = Categoria(nombre="Postres",   descripcion="Dulces", activo=True)

        for c in [cat_pizzas, cat_bebidas, cat_entradas, cat_postres]:
            session.add(c)
        session.flush()

        # ====================================================================
        # 5. INGREDIENTES (10)
        # ====================================================================
        print(" Sembrando Ingredientes...")
        ing_queso     = Ingrediente(nombre="Queso mozzarella",  stock=5.0, stock_seguridad=1.0, unidad_medida=UnidadMedida.KILOGRAMO, disponible=True, es_alergeno=False, costo_unitario=2000.0)
        ing_tomate    = Ingrediente(nombre="Salsa de tomate",   stock=4.0, stock_seguridad=1.0, unidad_medida=UnidadMedida.LITRO, disponible=True, es_alergeno=False, costo_unitario=500.0)
        ing_jamon     = Ingrediente(nombre="Jamón cocido",      stock=3.0, stock_seguridad=0.5, unidad_medida=UnidadMedida.KILOGRAMO, disponible=True, es_alergeno=False, costo_unitario=2000.0)
        ing_morron    = Ingrediente(nombre="Morrón",            stock=3.0, stock_seguridad=0.5, unidad_medida=UnidadMedida.KILOGRAMO, disponible=True, es_alergeno=False, costo_unitario=800.0)
        ing_aceitunas = Ingrediente(nombre="Aceitunas negras",  stock=2.0, stock_seguridad=0.5, unidad_medida=UnidadMedida.KILOGRAMO, disponible=True, es_alergeno=False, costo_unitario=1200.0)
        ing_cebolla   = Ingrediente(nombre="Cebolla",           stock=5.0, stock_seguridad=1.0, unidad_medida=UnidadMedida.KILOGRAMO, disponible=True, es_alergeno=False, costo_unitario=800.0)
        ing_huevo     = Ingrediente(nombre="Huevo",             stock=50.0, stock_seguridad=10.0, unidad_medida=UnidadMedida.UNIDAD, disponible=True, es_alergeno=True, costo_unitario=300.0)
        ing_lechuga   = Ingrediente(nombre="Lechuga",           stock=4.0, stock_seguridad=2.0, unidad_medida=UnidadMedida.KILOGRAMO, disponible=True, es_alergeno=False, costo_unitario=500.0)
        ing_carne     = Ingrediente(nombre="Carne molida",      stock=10.0, stock_seguridad=5.0, unidad_medida=UnidadMedida.KILOGRAMO, disponible=True, es_alergeno=False, costo_unitario=25000.0)
        ing_agua      = Ingrediente(nombre="Agua mineral",      stock=20.0, stock_seguridad=5.0, unidad_medida=UnidadMedida.UNIDAD, disponible=True, es_alergeno=False, costo_unitario=1000.0)

        ingredientes = [
            ing_queso, ing_tomate, ing_jamon, ing_morron, ing_aceitunas,
            ing_cebolla, ing_huevo, ing_lechuga, ing_carne, ing_agua,
        ]
        for i in ingredientes:
            session.add(i)
        session.flush()

        # ====================================================================
        # 6. PRODUCTOS (6) + ProductoCategoria + ProductoIngrediente
        # ====================================================================
        print(" Sembrando Productos con relaciones...")

        # --- Producto 1: Pizza Muzza ---
        prod_pizza_muzza = Producto(
            nombre="Pizza Muzza",
            descripcion="Pizza clásica con mozzarella derretida y salsa de tomate",
            imagen_url="https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            stock_cantidad=20,
            activo=True,
            costo_produccion=800.0,
            margen_ganancia=90.0,
            precio=5500.0,
        )
        session.add(prod_pizza_muzza)
        session.flush()

        session.add(ProductoCategoria(producto_id=prod_pizza_muzza.id, categoria_id=cat_pizzas.id))
        session.add(ProductoIngrediente(producto_id=prod_pizza_muzza.id, ingrediente_id=ing_queso.id,     cantidad_requerida=0.2, es_removible=False))
        session.add(ProductoIngrediente(producto_id=prod_pizza_muzza.id, ingrediente_id=ing_tomate.id,    cantidad_requerida=0.05, es_removible=False))

        # --- Producto 2: Pizza Napolitana ---
        prod_pizza_napo = Producto(
            nombre="Pizza Napolitana",
            descripcion="Pizza con mozzarella, tomate en rodajas, ajo y orégano",
            imagen_url="https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            stock_cantidad=15,
            activo=True,
            costo_produccion=1000.0,
            margen_ganancia=90.0,
            precio=6200.0,
        )
        session.add(prod_pizza_napo)
        session.flush()

        session.add(ProductoCategoria(producto_id=prod_pizza_napo.id, categoria_id=cat_pizzas.id))
        session.add(ProductoIngrediente(producto_id=prod_pizza_napo.id, ingrediente_id=ing_queso.id,     cantidad_requerida=0.2, es_removible=False))
        session.add(ProductoIngrediente(producto_id=prod_pizza_napo.id, ingrediente_id=ing_tomate.id,    cantidad_requerida=0.05, es_removible=False))
        session.add(ProductoIngrediente(producto_id=prod_pizza_napo.id, ingrediente_id=ing_jamon.id,     cantidad_requerida=0.1,  es_removible=True))
        session.add(ProductoIngrediente(producto_id=prod_pizza_napo.id, ingrediente_id=ing_morron.id,    cantidad_requerida=0.1,  es_removible=True))

        # --- Producto 3: Empanada de Carne ---
        prod_empanada = Producto(
            nombre="Empanada de Carne",
            descripcion="Empanada criolla con carne molida, cebolla y huevo duro",
            imagen_url="https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            stock_cantidad=40,
            activo=True,
            costo_produccion=250.0,
            margen_ganancia=90.0,
            precio=1200.0,
        )
        session.add(prod_empanada)
        session.flush()

        session.add(ProductoCategoria(producto_id=prod_empanada.id, categoria_id=cat_entradas.id))
        session.add(ProductoIngrediente(producto_id=prod_empanada.id, ingrediente_id=ing_carne.id,     cantidad_requerida=0.2, es_removible=False))
        session.add(ProductoIngrediente(producto_id=prod_empanada.id, ingrediente_id=ing_cebolla.id,  cantidad_requerida=0.1, es_removible=True))
        session.add(ProductoIngrediente(producto_id=prod_empanada.id, ingrediente_id=ing_huevo.id,    cantidad_requerida=1, es_removible=True))

        # --- Producto 4: Coca-Cola 500 ml ---
        prod_coca = Producto(
            nombre="Coca-Cola 500 ml",
            descripcion="Gaseosa Coca-Cola 500 ml",
            imagen_url="https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            stock_cantidad=50,
            activo=True,
            costo_produccion=400.0,
            margen_ganancia=50.0,
            precio=1000.0,
        )
        session.add(prod_coca)
        session.flush()

        session.add(ProductoCategoria(producto_id=prod_coca.id, categoria_id=cat_bebidas.id))

        # --- Producto 5: Agua Mineral ---
        prod_agua = Producto(
            nombre="Agua Mineral 500ml",
            descripcion="Agua mineral sin gas",
            imagen_url="https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            stock_cantidad=80,
            activo=True,
            costo_produccion=800.0,
            margen_ganancia=50.0,
            precio=1600.0,
        )
        session.add(prod_agua)
        session.flush()

        session.add(ProductoCategoria(producto_id=prod_agua.id, categoria_id=cat_bebidas.id))
        session.add(ProductoIngrediente(producto_id=prod_agua.id, ingrediente_id=ing_agua.id, cantidad_requerida=500.0, es_removible=False))

        # --- Producto 6: Flan Casero ---
        prod_flan = Producto(
            nombre="Flan Casero",
            descripcion="Flan de vainilla con dulce de leche y crema",
            imagen_url="https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            stock_cantidad=10,
            activo=True,
            costo_produccion=300.0,
            margen_ganancia=80.0,
            precio=1800.0,
        )
        session.add(prod_flan)
        session.flush()

        session.add(ProductoCategoria(producto_id=prod_flan.id, categoria_id=cat_postres.id))
        session.add(ProductoIngrediente(producto_id=prod_flan.id, ingrediente_id=ing_huevo.id, cantidad_requerida=50.0, es_removible=False))

        # ====================================================================
        # 7. DIRECCIONES DE ENTREGA (3) — para pepe@gmail.com
        # ====================================================================
        print(" Sembrando Direcciones de Entrega...")
        dir_casa = DireccionEntrega(
            usuario_id=cliente_user.id,
            alias="Casa",
            calle="San Martín",
            numero="1234",
            piso=None,
            departamento=None,
            ciudad="Mendoza",
            codigo_postal="M5500",
            predeterminada=True,
        )
        session.add(dir_casa)
        session.flush()

        dir_trabajo = DireccionEntrega(
            usuario_id=cliente_user.id,
            alias="Trabajo",
            calle="Av. San Juan",
            numero="456",
            piso="3",
            departamento="B",
            ciudad="Mendoza",
            codigo_postal="M5500",
            predeterminada=False,
        )
        session.add(dir_trabajo)
        session.flush()

        dir_playa = DireccionEntrega(
            usuario_id=cliente_user.id,
            alias="Casa de Playa",
            calle="Los Álamos",
            numero="89",
            piso=None,
            departamento=None,
            ciudad="San Rafael",
            codigo_postal="M5600",
            predeterminada=False,
        )
        session.add(dir_playa)
        session.flush()

        # ====================================================================
        # 8. PEDIDOS DE MUESTRA (3) — para pepe@gmail.com
        # ====================================================================
        print(" Sembrando Pedidos de muestra...")

        # --- Pedido 1: ENTREGADO (delivery, efectivo) ---
        ahora = datetime.utcnow()
        pedido1 = Pedido(
            usuario_id=cliente_user.id,
            direccion_id=dir_casa.id,
            estado_codigo=EstadoPedido.ENTREGADO,
            forma_pago_codigo=FormaPago.EFECTIVO.value,
            tipo_entrega=TipoEntrega.DELIVERY.value,
            subtotal=10800.0,
            descuento=0.0,
            costo_envio=1000.0,
            total=11800.0,
            notas="Sin острый",
            creado_en=ahora,
            actualizado_en=ahora,
        )
        session.add(pedido1)
        session.flush()

        # DetallePedido 1.1
        session.add(DetallePedido(
            pedido_id=pedido1.id,
            producto_id=prod_pizza_muzza.id,
            cantidad=1,
            nombre_snapshot="Pizza Muzza",
            precio_snapshot=5500.0,
            subtotal_snap=5500.0,
            personalizacion=None,
        ))
        # DetallePedido 1.2
        session.add(DetallePedido(
            pedido_id=pedido1.id,
            producto_id=prod_coca.id,
            cantidad=1,
            nombre_snapshot="Coca-Cola 1.5L",
            precio_snapshot=2500.0,
            subtotal_snap=2500.0,
            personalizacion=None,
        ))
        # DetallePedido 1.3
        session.add(DetallePedido(
            pedido_id=pedido1.id,
            producto_id=prod_agua.id,
            cantidad=1,
            nombre_snapshot="Agua Mineral 500ml",
            precio_snapshot=800.0,
            subtotal_snap=800.0,
            personalizacion=None,
        ))

        # HistorialPedido 1
        for idx, (desde, hacia, minutos) in enumerate([
            (None,                        EstadoPedido.PENDIENTE.value,     0),
            (EstadoPedido.PENDIENTE.value,    EstadoPedido.CONFIRMADO.value,     5),
            (EstadoPedido.CONFIRMADO.value,    EstadoPedido.EN_PREPARACION.value, 15),
            (EstadoPedido.EN_PREPARACION.value, EstadoPedido.EN_CAMINO.value,      45),
            (EstadoPedido.EN_CAMINO.value,      EstadoPedido.ENTREGADO.value,      90),
        ]):
            session.add(HistorialEstadoPedido(
                pedido_id=pedido1.id,
                estado_desde=desde,
                estado_hacia=hacia,
                usuario_id=admin_user.id if idx > 0 else None,
                motivo="Se entrega en puerta" if idx == 4 else None,
                creado_en=datetime.fromtimestamp(ahora.timestamp() + minutos * 60, tz=ahora.tzinfo),
            ))

        # --- Pedido 2: EN_PREPARACION (delivery, mercadopago) ---
        pedido2 = Pedido(
            usuario_id=cliente_user.id,
            direccion_id=dir_trabajo.id,
            estado_codigo=EstadoPedido.EN_PREPARACION,
            forma_pago_codigo=FormaPago.MERCADOPAGO.value,
            tipo_entrega=TipoEntrega.DELIVERY.value,
            subtotal=12400.0,
            descuento=0.0,
            costo_envio=800.0,
            total=13200.0,
            notas="Por favor sin morrón en ninguna",
            creado_en=ahora,
            actualizado_en=ahora,
        )
        session.add(pedido2)
        session.flush()

        # DetallePedido 2.1 (sin morrón → personalizacion=[morron.id])
        session.add(DetallePedido(
            pedido_id=pedido2.id,
            producto_id=prod_pizza_napo.id,
            cantidad=2,
            nombre_snapshot="Pizza Napolitana",
            precio_snapshot=6200.0,
            subtotal_snap=12400.0,
            personalizacion=[ing_morron.id],
        ))

        # HistorialPedido 2
        for idx, (desde, hacia, minutos) in enumerate([
            (None,                              EstadoPedido.PENDIENTE.value,         0),
            (EstadoPedido.PENDIENTE.value,         EstadoPedido.CONFIRMADO.value,         3),
            (EstadoPedido.CONFIRMADO.value,         EstadoPedido.EN_PREPARACION.value,     8),
        ]):
            session.add(HistorialEstadoPedido(
                pedido_id=pedido2.id,
                estado_desde=desde,
                estado_hacia=hacia,
                usuario_id=admin_user.id if idx > 0 else None,
                motivo=None,
                creado_en=datetime.fromtimestamp(ahora.timestamp() + minutos * 60, tz=ahora.tzinfo),
            ))

        # --- Pedido 3: PENDIENTE (en local, efectivo) ---
        pedido3 = Pedido(
            usuario_id=cliente_user.id,
            direccion_id=None,  # en local
            estado_codigo=EstadoPedido.PENDIENTE,
            forma_pago_codigo=FormaPago.EFECTIVO.value,
            tipo_entrega=TipoEntrega.EN_LOCAL.value,
            subtotal=5400.0,
            descuento=0.0,
            costo_envio=0.0,
            total=5400.0,
            notas=None,
            creado_en=ahora,
            actualizado_en=ahora,
        )
        session.add(pedido3)
        session.flush()

        # DetallePedido 3.1
        session.add(DetallePedido(
            pedido_id=pedido3.id,
            producto_id=prod_empanada.id,
            cantidad=3,
            nombre_snapshot="Empanada de Carne",
            precio_snapshot=1200.0,
            subtotal_snap=3600.0,
            personalizacion=None,
        ))
        # DetallePedido 3.2
        session.add(DetallePedido(
            pedido_id=pedido3.id,
            producto_id=prod_flan.id,
            cantidad=1,
            nombre_snapshot="Flan Casero",
            precio_snapshot=1800.0,
            subtotal_snap=1800.0,
            personalizacion=None,
        ))

        # HistorialPedido 3 (solo creación)
        session.add(HistorialEstadoPedido(
            pedido_id=pedido3.id,
            estado_desde=None,
            estado_hacia=EstadoPedido.PENDIENTE.value,
            usuario_id=None,
            motivo=None,
        ))

        # ====================================================================
        # 9. PAGOS DE MERCADOPAGO (1) — para pedido2
        # ====================================================================
        print(" Sembrando Pagos de prueba...")
        session.add(Pago(
            pedido_id=pedido2.id,
            mp_payment_id=1234567890,
            mp_status="approved",
            mp_status_detail="accredited",
            transaction_amount=13200.0,
            payment_method_id="visa",
            external_reference=f"PED-{pedido2.id:06d}",
            idempotency_key=f"idemp-pedido2-{pedido2.id}",
            preference_id="preference-test-001",
            init_point="https://www.mercadopago.com.ar/checkout/v1/redirect?pref_test=001",
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
    print("CATÁLOGO SEMILLADO:")
    print("  5 Categorías:  Pizzas, Bebidas, Entradas, Postres, Combos")
    print("  10 Ingredientes: Queso mozzarella, Salsa de tomate, Jamón cocido,")
    print("                   Morrón, Aceitunas negras, Cebolla, Huevo,")
    print("                   Lechuga, Carne molida, Agua mineral")
    print("  6 Productos:   Pizza Muzza, Pizza Napolitana, Empanada de Carne,")
    print("                 Coca-Cola 1.5L, Agua Mineral 500ml, Flan Casero")
    print("=======================================================================")
    print("PEDIDOS Y OPERACIONES:")
    print("  3 Direcciones (Casa, Trabajo, Casa de Playa) para pepe@gmail.com")
    print("  3 Pedidos:")
    print("    #1 ENTREGADO     - delivery, efectivo  - 1xPizzaMuzza+1xCoca+1xAgua")
    print("    #2 EN_PREPARACION- delivery, MPago    - 2xPizzaNapolitana (sin morrón)")
    print("    #3 PENDIENTE     - en local, efectivo - 3xEmpanadas+1xFlan")
    print("  ~10 Detalles de pedido")
    print("  ~10 Entradas en historial de estados")
    print("  1 Pago de MercadoPago (aprobado) → pedido #2")
    print("=======================================================================")


if __name__ == "__main__":
    inicializar_sistema()
