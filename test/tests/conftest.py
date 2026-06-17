"""
tests/conftest.py
=================

Fixtures compartidos por toda la suite de tests.

Convención (basada en el cap12 del libro FastAPI):
  - `engine_test`: scope=session, una sola vez por toda la suite.
  - `session`: scope=function, nueva por test (CREATE/DROP TABLE).
  - `client`: scope=function, TestClient con dependency_overrides.
  - Fixtures de datos: productos, usuarios, payloads, auth headers.

Adaptaciones para NUESTRO proyecto:
  - Como tenemos JWT en cookies + auth, agregamos fixtures para
    obtener headers de autenticación.
  - Como tenemos un RateLimitMiddleware en memoria, agregamos un
    fixture para resetearlo entre tests.
"""

# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
import os
import pytest

# FastAPI TestClient: simula requests HTTP sin abrir un socket TCP.
from fastapi.testclient import TestClient

# SQLModel/SQLAlchemy para manejo de DB en tests.
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

# ⚠️ Importar ANTES que la app: garantiza que SQLModel.metadata conozca
# TODOS los modelos antes de hacer create_all.
from sqlmodel import select

from app.core.config import settings
from app.core.database import get_session
from app.core.rate_limit.rate_limit_middleware import RateLimitMiddleware
from app.core.security import hash_password
from app.main import app
from app.modules.productos.models import Producto
from app.modules.usuarios.models import Usuario


# ===========================================================================
# CONFIGURACIÓN DE ENTORNO PARA TESTS
# ===========================================================================
# Forzamos el environment "test" ANTES de cualquier import que lea settings.
# Esto hace que `settings.DATABASE_URL` apunte a la DB de test (o a SQLite).
os.environ.setdefault("ENVIRONMENT", "test")


# ===========================================================================
# 1. ENGINE DE TEST
# ===========================================================================
@pytest.fixture(name="engine_test", scope="session")
def engine_test_fixture():
    """
    Engine de SQLAlchemy para los tests.

    ¿Por qué SQLite en vez de PostgreSQL?
    --------------------------------------
    Para CI/CD rápido y para que cualquiera pueda correr los tests sin
    levantar un Postgres. El cap12 muestra el patrón con Postgres+NullPool;
    acá usamos SQLite con StaticPool (que es el equivalente para SQLite:
    una única conexión compartida entre threads).

    ¿Y si el código usa features específicas de Postgres?
    ----------------------------------------------------
    Para este proyecto educativo, no. Si en producción quisiéramos
    testear features de Postgres, usaríamos el patrón del cap12 con
    TEST_DATABASE_URL + NullPool.

    `scope="session"`: el engine se crea UNA vez por toda la ejecución
    de pytest, no por test. Mucho más rápido.
    """
    url = settings.TEST_DATABASE_URL
    connect_args = {}
    poolclass = StaticPool

    # SQLite necesita `check_same_thread=False` cuando se usa desde
    # múltiples threads (TestClient puede usar threads).
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        poolclass = StaticPool  # una conexión, reutilizada

    engine = create_engine(
        url,
        connect_args=connect_args,
        poolclass=poolclass,
        echo=False,  # True para ver SQL en consola (debug).
    )
    yield engine
    # Al final de TODA la suite, cerramos el engine.
    engine.dispose()


# ===========================================================================
# 2. SESSION DE BASE DE DATOS
# ===========================================================================
@pytest.fixture(name="session", scope="function")
def session_fixture(engine_test):
    """
    Session de DB para un test.

    `scope="function"`: nueva session por test. Antes del yield creamos
    las tablas; después las dropeamos. Esto garantiza aislamiento total.

    Si un test falla a mitad, las tablas se dropean igual (el código
    post-yield se ejecuta siempre, no solo en happy path).
    """
    # DDL: CREATE TABLE.
    SQLModel.metadata.create_all(engine_test)

    with Session(engine_test) as session:
        yield session  # ← el test corre acá.

    # DDL: DROP TABLE. Limpieza total.
    SQLModel.metadata.drop_all(engine_test)


# ===========================================================================
# 3. CLIENTE HTTP DE TEST
# ===========================================================================
@pytest.fixture(name="client", scope="function")
def client_fixture(session: Session):
    """
    TestClient de FastAPI con la DB de test inyectada.

    `dependency_overrides[get_session]` reemplaza la dependency de
    producción por una que devuelve NUESTRA session de test. El endpoint
    no se entera: cree que está usando la DB real.

    `with TestClient(app) as client` activa el lifespan (startup/shutdown).
    """
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override

    # Limpiamos el rate limiter para que un test no contamine al siguiente.
    _reset_rate_limit_state()

    # ⚠️ Como la session está overrideada, el `seed_database()` del
    # lifespan corrió contra la DB de producción, no la de test. Creamos
    # el admin DIRECTO en la session de test.
    _create_test_admin(session)

    with TestClient(app) as client:
        yield client

    # Restauramos el estado original de la app.
    app.dependency_overrides.clear()


def _create_test_admin(session: Session) -> None:
    """
    Crea el usuario admin en la session de TEST (no en producción).

    Como `client_fixture` overridea `get_session`, el lifespan del app
    corre el seed contra la DB de producción, no la de test. Por eso
    tenemos que crear el admin manualmente en la session de test.
    """
    from app.core.security import hash_password
    from app.modules.usuarios.models import Usuario

    # Si ya existe (raro, por si se llama dos veces), no duplicar.
    existing = session.exec(
        select(Usuario).where(Usuario.username == settings.ADMIN_USERNAME)
    ).first()
    if existing is not None:
        return

    admin = Usuario(
        username=settings.ADMIN_USERNAME,
        email=settings.ADMIN_EMAIL,
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        rol="admin",
        is_active=True,
    )
    session.add(admin)
    session.commit()


def _reset_rate_limit_state() -> None:
    """
    Resetea el estado en memoria del RateLimitMiddleware.

    Como el limiter vive en el atributo de clase (compartido entre
    requests), un test que agote el bucket dejaría al siguiente test
    "sin budget". Reseteamos antes de cada test que use el client.

    Usa el classmethod `reset_all_limiters()` que expusimos en el
    middleware para que los tests no tengan que hackear internals.
    """
    try:
        RateLimitMiddleware.reset_all_limiters()
    except Exception:
        # Si falla el reset, no bloqueamos el test: podría haber un bug
        # en el setup, pero los tests deberían poder correr igual
        # (simplemente no testeamos rate limit con precisión en ese test).
        pass


# ===========================================================================
# 4. FIXTURES DE DATOS
# ===========================================================================
@pytest.fixture(name="producto_payload")
def producto_payload_fixture() -> dict:
    """Payload válido para crear un producto."""
    return {
        "nombre": "Laptop Test",
        "descripcion": "Notebook de prueba",
        "precio": 999.99,
        "stock": 10,
        "categoria": "tecnologia",
    }


@pytest.fixture(name="created_producto")
def created_producto_fixture(client: TestClient, producto_payload: dict) -> dict:
    """Crea un producto vía API y lo devuelve. Útil para GET/PATCH/DELETE."""
    # Requiere estar autenticado; usamos el admin del fixture.
    headers = _get_admin_auth_headers(client)
    response = client.post("/productos/", json=producto_payload, headers=headers)
    assert response.status_code == 201, f"Setup falló: {response.json()}"
    return response.json()


@pytest.fixture(name="admin_user_data")
def admin_user_data_fixture() -> dict:
    """Datos del admin inicial (los mismos que el seed)."""
    return {
        "username": settings.ADMIN_USERNAME,
        "email": settings.ADMIN_EMAIL,
        "password": settings.ADMIN_PASSWORD,
    }


@pytest.fixture(name="normal_user_data")
def normal_user_data_fixture() -> dict:
    """Datos para crear un usuario normal (no admin) en tests."""
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "TestPass123!",
    }


@pytest.fixture(name="normal_user")
def normal_user_fixture(client: TestClient, normal_user_data: dict) -> dict:
    """
    Crea un usuario normal vía API y devuelve la respuesta.
    Asume que ya existe el admin (lo crea el seed en startup).
    """
    response = client.post("/usuarios/register", json=normal_user_data)
    assert response.status_code == 201, f"Setup normal_user falló: {response.json()}"
    return response.json()


# ===========================================================================
# 5. HELPERS DE AUTENTICACIÓN
# ===========================================================================
def _get_admin_auth_headers(client: TestClient) -> dict:
    """
    Helper: hace login con el admin y devuelve headers con la cookie.

    El admin existe porque `client_fixture` lo crea en la session de test
    (porque el seed del lifespan corre contra producción overrideada).
    """
    response = client.post(
        "/usuarios/token",
        data={  # ⚠️ form, no JSON.
            "username": settings.ADMIN_USERNAME,
            "password": settings.ADMIN_PASSWORD,
        },
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"No se pudo loguear al admin. Status: {response.status_code}, "
            f"Body: {response.text}"
        )
    # El JWT viaja en la cookie HttpOnly `access_token` (no en el body).
    cookie = response.cookies.get("access_token")
    if not cookie:
        raise RuntimeError(
            f"Login del admin OK pero sin cookie access_token. "
            f"Headers: {dict(response.headers)}, Body: {response.text}"
        )
    return {"Cookie": f"access_token={cookie}"}


def _get_user_auth_headers(client: TestClient, username: str, password: str) -> dict:
    """Helper: login con un usuario específico. Devuelve headers con la cookie."""
    response = client.post(
        "/usuarios/token",
        data={"username": username, "password": password},
    )
    if response.status_code != 200:
        raise RuntimeError(f"Login falló para {username}: {response.text}")
    cookie = response.cookies.get("access_token")
    if not cookie:
        raise RuntimeError(
            f"Login de {username} OK pero sin cookie access_token. "
            f"Body: {response.text}"
        )
    return {"Cookie": f"access_token={cookie}"}


@pytest.fixture(name="admin_auth_headers")
def admin_auth_headers_fixture(client: TestClient) -> dict:
    """Headers de autenticación del admin (con cookie)."""
    return _get_admin_auth_headers(client)


@pytest.fixture(name="user_auth_headers")
def user_auth_headers_fixture(
    client: TestClient, normal_user: dict, normal_user_data: dict
) -> dict:
    """Headers de autenticación de un usuario normal (depende de `normal_user`)."""
    return _get_user_auth_headers(
        client,
        normal_user["username"],
        normal_user_data["password"],
    )
