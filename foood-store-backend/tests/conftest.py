"""
conftest.py — Fixtures compartidos para toda la suite de tests.
============================================================================
Usa PostgreSQL real para tests (la app usa ARRAY(Integer) que SQLite no soporta).

Setup:
1. Crear BD de test:  CREATE DATABASE foodstore_test_db;
2. Asegurarse de que .env.test tenga: TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/foodstore_test_db
3. Crear tablas:     alembic upgrade head
4. Seed inicial:      python init_db.py  (una sola vez después de crear la BD)

Fixtures disponibles:
- engine, db_session   → BD de test limpia por test (rollback automático)
- client               → TestClient de FastAPI
- test_user            → usuario CLIENTE pre-creado
- test_admin           → usuario ADMIN pre-creado
- test_producto        → producto de catálogo pre-creado
- auth_headers          → helper que devuelve headers con JWT del usuario
"""
import os
import sys
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

# Cargar .env.test ANTES de importar la app
ENV_TEST_PATH = os.path.join(os.path.dirname(__file__), "..", ".env.test")
if os.path.exists(ENV_TEST_PATH):
    from dotenv import load_dotenv
    load_dotenv(ENV_TEST_PATH, override=True)

from main import app
from core.security import create_access_token, get_password_hash
from app.modules.usuario.models import Usuario, Rol, UsuarioRol
from app.modules.catalogo.producto.models import Producto
from app.modules.catalogo.categoria.models import Categoria
from app.modules.direccion.models import DireccionEntrega


# ─── Engine de test ──────────────────────────────────────────────────────────
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/foodstore_test_db",
)

# NullPool: cada conexión se cierra inmediatamente (ideal para tests paralelos)
engine = create_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)

# Para que PostgreSQL createdb funcione en tests: recreate Foreign Key constraints
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """No-op para PostgreSQL (solo tiene efecto en SQLite)."""
    pass


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Crea todas las tablas antes del test y las dropea después.
    Cada test tiene su propia transacción que hace rollback al terminar.
    """
    # Crear tablas (si no existen)
    SQLModel.metadata.create_all(bind=engine)

    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient con override de get_session para usar la sesión de test."""

    def _override_get_session():
        yield db_session

    app.dependency_overrides[get_session_from_core()] = _override_get_session

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def get_session_from_core():
    """Import deferred para evitar circular imports."""
    from core.database import get_session
    return get_session


# ─── Fixtures: datos de prueba ───────────────────────────────────────────────

@pytest.fixture(scope="function")
def test_admin(db_session: Session) -> Usuario:
    """Crea y devuelve un usuario ADMIN en la sesión de test."""
    # Dropear tablas antes para partir limpio (la BD de test es compartida)
    admin = Usuario(
        email="test_admin@foodstore.test",
        password=get_password_hash("admin123"),
        nombre="Admin",
        apellido="Test",
        cel="1111111111",
        activo=True,
    )
    db_session.add(admin)
    db_session.flush()

    # Asignar rol ADMIN
    rol_admin = db_session.exec(
        __import__("sqlmodel").select(Rol).where(Rol.codigo == "ADMIN")
    ).first()
    if rol_admin:
        db_session.add(UsuarioRol(usuario_id=admin.id, rol_codigo=rol_admin.codigo))
        db_session.flush()

    return admin


@pytest.fixture(scope="function")
def test_user(db_session: Session) -> Usuario:
    """Crea y devuelve un usuario CLIENTE en la sesión de test."""
    user = Usuario(
        email="test_cliente@foodstore.test",
        password=get_password_hash("cliente123"),
        nombre="Cliente",
        apellido="Test",
        cel="2222222222",
        activo=True,
    )
    db_session.add(user)
    db_session.flush()

    # Asignar rol CLIENTE
    rol_cliente = db_session.exec(
        __import__("sqlmodel").select(Rol).where(Rol.codigo == "CLIENTE")
    ).first()
    if rol_cliente:
        db_session.add(UsuarioRol(usuario_id=user.id, rol_codigo=rol_cliente.codigo))
        db_session.flush()

    return user


@pytest.fixture(scope="function")
def test_producto(db_session: Session) -> Producto:
    """Crea y devuelve un producto de catálogo."""
    producto = Producto(
        nombre="Pizza Margherita",
        descripcion="Pizza clásica italiana",
        precio=1500.0,
        stock_cantidad=50,
        activo=True,
    )
    db_session.add(producto)
    db_session.flush()
    return producto


@pytest.fixture(scope="function")
def test_direccion(db_session: Session, test_user: Usuario) -> DireccionEntrega:
    """Crea una dirección de entrega para el usuario de test."""
    direccion = DireccionEntrega(
        usuario_id=test_user.id,
        calle="Av. Test",
        numero="123",
        piso=None,
        depto=None,
        ciudad="TestCiudad",
        provincia="TestProvincia",
        cp="1000",
        referencia="Referencia test",
    )
    db_session.add(direccion)
    db_session.flush()
    return direccion


# ─── Helpers ────────────────────────────────────────────────────────────────

def auth_headers(user: Usuario, db_session: Session) -> dict:
    """Genera headers con JWT válido para el usuario dado."""
    # Extraer roles del usuario
    from sqlmodel import select
    roles = db_session.exec(
        select(UsuarioRol.rol_codigo).where(UsuarioRol.usuario_id == user.id)
    ).all()

    token = create_access_token(
        subject=str(user.id),
        roles=list(roles) if roles else ["CLIENTE"],
    )
    return {"Authorization": f"Bearer {token}"}


def admin_headers(db_session: Session) -> dict:
    """Genera headers con JWT de admin."""
    from sqlmodel import select
    admin = db_session.exec(select(Usuario).where(Usuario.email == "test_admin@foodstore.test")).first()
    if not admin:
        pytest.skip("test_admin fixture no disponible")
    return auth_headers(admin, db_session)
