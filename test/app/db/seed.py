"""
Módulo: app/db/seed.py
======================

Script de **seeding** (carga inicial de datos) de la base de datos.

¿Qué hace?
----------
Al iniciar la app, garantiza que existan:
  - Un usuario admin (configurable vía .env).
  - Algunos productos de ejemplo (solo si la tabla está vacía).

¿Por qué un seed?
-----------------
  1. **Demo/dev**: para que el developer pueda probar la app sin tener
     que crear usuarios a mano.
  2. **Tests**: podemos llamar `seed_database()` desde conftest.py para
     tener un estado conocido.
  3. **Producción**: aunque NO querríamos crear un admin hardcodeado en
     producción (vulnerabilidad), podríamos querer crear catálogos
     iniciales (países, monedas, roles). En este proyecto educativo,
     asumimos dev/demo.

Idempotencia:
-------------
"Idempotente" significa que podés correrlo 1 vez o 100 veces y el
resultado es el mismo. Lo logramos con `if not exists` antes de cada
INSERT.
"""

# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
# `select` para chequear si ya existe.
from sqlmodel import Session, select

# Config: leemos credenciales del admin desde .env.
from app.core.config import settings

# Función para hashear la contraseña del admin.
from app.core.security import hash_password

# Nuestra función que crea el engine.
from app.core.database import create_all_tables, engine

# Modelos.
from app.modules.productos.models import Producto
from app.modules.usuarios.models import Usuario


# ---------------------------------------------------------------------------
# FUNCIÓN: create_admin_user
# ---------------------------------------------------------------------------
def create_admin_user(session: Session) -> None:
    """
    Crea el usuario admin inicial si NO existe.

    Lee username, email y password desde `settings` (variables .env).
    Por seguridad, el .env de PRODUCCIÓN debe sobrescribir estos valores
    (o este seed debería desactivarse en producción).
    """
    # Chequeamos si ya existe por username.
    statement = select(Usuario).where(Usuario.username == settings.ADMIN_USERNAME)
    existing = session.exec(statement).first()

    if existing is not None:
        # Ya existe → no hacemos nada. Esto es lo que hace el seed
        # idempotente: re-ejecuciones no fallan ni duplican.
        return

    # Creamos el admin.
    admin = Usuario(
        username=settings.ADMIN_USERNAME,
        email=settings.ADMIN_EMAIL,
        # ⚠️ NUNCA guardamos plaintext. Hasheamos con bcrypt.
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        rol="admin",          # este es el ÚNICO admin inicial del sistema.
        is_active=True,
    )
    session.add(admin)
    # El commit lo hace el caller (seed_database) para que sea atómico
    # con el resto del seed.
    return


# ---------------------------------------------------------------------------
# FUNCIÓN: create_sample_products
# ---------------------------------------------------------------------------
def create_sample_products(session: Session) -> None:
    """
    Carga productos de ejemplo SOLO si la tabla está vacía.

    Esto evita duplicar el catálogo si el seed corre varias veces.
    En un sistema real, los productos se cargan desde archivos de
    migración o desde un panel de admin.
    """
    statement = select(Producto)
    existing = session.exec(statement).first()

    if existing is not None:
        # Ya hay productos → no cargamos.
        return

    # Lista de productos de ejemplo. Variedad de categorías y precios.
    sample_products = [
        Producto(nombre="Laptop Pro 14", descripcion="Notebook 14 pulgadas, 16GB RAM, 512GB SSD.", precio=1499.99, stock=10, categoria="tecnologia"),
        Producto(nombre="Mouse Inalámbrico", descripcion="Mouse ergonómico Bluetooth.", precio=29.99, stock=50, categoria="tecnologia"),
        Producto(nombre="Silla Ergonómica", descripcion="Silla de oficina con soporte lumbar.", precio=349.00, stock=15, categoria="oficina"),
        Producto(nombre="Libro: Clean Code", descripcion="Robert C. Martin.", precio=35.50, stock=25, categoria="libros"),
        Producto(nombre="Cafetera Express", descripcion="Cafetera automática 15 bar.", precio=599.00, stock=8, categoria="hogar"),
    ]

    for p in sample_products:
        session.add(p)

    return


# ---------------------------------------------------------------------------
# FUNCIÓN: seed_database (entrypoint)
# ---------------------------------------------------------------------------
def seed_database() -> None:
    """
    Punto de entrada del seeding. Idempotente: corre todas las veces
    que quieras, solo crea lo que falta.

    Llamada típica: en el `lifespan` de FastAPI al iniciar la app.

    ¿Por qué crear las tablas acá también?
    ---------------------------------------
    En producción usarías Alembic. Para este proyecto educativo,
    `create_all_tables()` es suficiente: crea todas las tablas que
    SQLModel.metadata conoce. Es idempotente a nivel DB (CREATE TABLE
    IF NOT EXISTS no existe en Postgres puro, pero SQLAlchemy chequea
    primero).
    """
    # Primero, nos aseguramos de que existan las tablas.
    create_all_tables()

    # Abrimos una session y corremos los seeds dentro de una transacción.
    with Session(engine) as session:
        try:
            create_admin_user(session)
            create_sample_products(session)
            session.commit()
        except Exception:
            # Si algo falla, rollback para no dejar la DB a medio camino.
            session.rollback()
            # Re-lanzamos para que el caller (lifespan) sepa que falló.
            raise


# ---------------------------------------------------------------------------
# EJECUCIÓN DIRECTA
# ---------------------------------------------------------------------------
# Si corrés `python -m app.db.seed`, ejecuta el seed manualmente.
# Útil para setup inicial desde la terminal sin levantar la API.
if __name__ == "__main__":
    seed_database()
    print("Seed ejecutado OK.")
