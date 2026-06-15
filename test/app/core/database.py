# =============================================================================
# database.py — Engine SQLModel y factory de sesiones
# =============================================================================
#
# CONCEPTO CLAVE: el engine y la session
# ----------------------------------------------------
# - ENGINE: objeto pesado que mantiene un POOL de conexiones a la BD.
#   Es un SINGLETON: se crea UNA vez al importar este módulo y se reutiliza.
# - SESSION: objeto liviano que representa una "transacción lógica".
#   Se crea UNA por request y se cierra al terminar.
#
# ¿POR QUÉ yield EN get_session()?
# ----------------------------------------------------
# FastAPI ejecuta dependencias ANTES del endpoint y DESPUÉS (cleanup).
# El `yield` permite hacer setup → ejecutar el endpoint → cleanup.
# Equivale a un context manager (with Session() as s:) pero compatible
# con el sistema de Dependency Injection de FastAPI.
# =============================================================================

from sqlmodel import SQLModel, Session, create_engine

from app.core.config import settings


# ─── Engine singleton ────────────────────────────────────────────────────────
# echo=False: NO loguear cada query SQL (es muy verboso en producción).
# En debugging, cambiar a True temporalmente.
# pool_pre_ping=True: detecta conexiones muertas antes de usarlas.
#   Útil cuando la BD se reinicia y el pool tiene conexiones "stale".
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)


def get_session():
    """
    Dependencia FastAPI que provee una sesión por request.

    Flujo:
        1. FastAPI llama a esta función antes de ejecutar el endpoint.
        2. Se abre una nueva Session con el engine global.
        3. `yield session` entrega la sesión al endpoint.
        4. Después del endpoint, FastAPI ejecuta el código post-yield
           (en este caso, nada — el with se encarga del close()).

    Equivale a:
        with Session(engine) as session:
            yield session
    Pero más explícito y testeable.
    """
    with Session(engine) as session:
        yield session


def create_all_tables() -> None:
    """
    Crea las tablas en la BD si no existen.

    Llamado al arrancar la app (lifespan). Los imports de los modelos
    los REGISTRAN en SQLModel.metadata (efecto colateral del import).
    Sin esos imports, create_all() no encontraría las tablas a crear.

    En producción se prefiere Alembic (migraciones versionadas). Esta
    función queda como conveniencia para desarrollo y tests.
    """
    # Los imports registran los modelos en SQLModel.metadata.
    # noqa evita warnings de "imported but unused" — el efecto es el import.
    from app.modules.usuarios.models import Usuario  # noqa: F401
    from app.modules.productos.models import Producto  # noqa: F401

    SQLModel.metadata.create_all(engine)
