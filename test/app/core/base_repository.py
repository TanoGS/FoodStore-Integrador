"""
Módulo: app/core/base_repository.py
====================================

¿Qué hace este archivo?
------------------------
Define el **Repository genérico**: una clase base que provee operaciones
CRUD fundamentales sobre cualquier modelo SQLModel. Cada módulo hereda
de `BaseRepository[T]` y agrega queries específicas.

Patrón Repository (revisado):
-----------------------------
El Repository **oculta la complejidad del ORM** detrás de métodos del
dominio. En vez de que el Service escriba SQL o use `select(Usuario)`,
llama a métodos claros como `get_by_id()`, `add()`, `update()`.

Diferencia con el patrón de muchos tutoriales:
-----------------------------------------------
  - Repositorio "puro" (DDD estricto): cada operación recibe `session`
    por parámetro. Más funcional, más testeable.
  - Repositorio "con estado" (el que usamos acá): la session vive en
    `self.session` (inyectada en el __init__). Más simple, menos
    ceremonia, suficiente para 99% de los casos.

Herencia del UoW:
-----------------
El Repository NO maneja transacciones. La session la creó el engine, la
transacción la maneja el Unit of Work. El Repository solo ejecuta
queries sobre la session que ya está abierta.
"""

# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
# `TypeVar` para hacer el Repository genérico (T puede ser cualquier modelo).
from typing import Generic, Type, TypeVar

# SQLModel + select para queries type-safe.
from sqlmodel import SQLModel, Session, select


# TypeVar genérico: T debe ser una subclase de SQLModel (tabla).
T = TypeVar("T", bound=SQLModel)


# ---------------------------------------------------------------------------
# CLASE: BaseRepository
# ---------------------------------------------------------------------------
class BaseRepository(Generic[T]):
    """
    Repository genérico con CRUD base para cualquier modelo SQLModel.

    Cómo se usa:
    ------------
        class UsuarioRepository(BaseRepository[Usuario]):
            def __init__(self, session: Session):
                # Pasamos la CLASE del modelo (no una instancia) y la session.
                super().__init__(Usuario, session)

            def get_by_username(self, username: str) -> Usuario | None:
                return self.session.exec(
                    select(Usuario).where(Usuario.username == username)
                ).first()

    ⚠️ Importante: los métodos base NO reciben `session` por parámetro.
    Usan `self.session` (la que se inyectó en __init__). El Service obtiene
    la session UNA vez del UoW, y todas las operaciones del Repository
    usan esa misma session/transacción.
    """

    def __init__(self, model: Type[T], session: Session) -> None:
        """
        Args:
            model: la CLASE del modelo (ej: `Usuario`, no `Usuario(...)`).
                   La guardamos para hacer queries genéricas.
            session: la sesión activa de SQLAlchemy/SQLModel. La recibimos
                     ya abierta (la creó el engine, la transacciona el UoW).
        """
        self.model = model      # la clase, no una instancia
        self.session = session  # sesión activa

    # -----------------------------------------------------------------------
    # get_by_id
    # -----------------------------------------------------------------------
    def get_by_id(self, entity_id: int) -> T | None:
        """
        Busca una entidad por su primary key.

        Equivale a `SELECT * FROM tabla WHERE id = ? LIMIT 1`.

        Devuelve `None` si no existe (no lanza excepción). Esto es por
        convención: "no encontrado" no es un error de sistema, es un
        caso esperado. Quien llama (el Service) decide qué hacer.
        """
        # `session.get(model, id)` es la forma idiomática de SQLAlchemy
        # para buscar por PK. Más eficiente que `select().where()` porque
        # usa el identity map de la session.
        return self.session.get(self.model, entity_id)

    # -----------------------------------------------------------------------
    # get_all
    # -----------------------------------------------------------------------
    def get_all(self) -> list[T]:
        """
        Devuelve TODAS las filas de la tabla.

        ⚠️ PELIGRO: en tablas grandes esto puede traer miles de filas a
        memoria. En producción SIEMPRE se debería paginar con `skip` y
        `limit`. Lo dejamos como base para el caso de tablas pequeñas
        (categorías, roles, etc.) y que las subclases agreguen paginación.
        """
        # `select(self.model)` → `SELECT * FROM tabla`.
        # `.exec(query)` ejecuta y devuelve un Result iterable.
        # `.all()` materializa todo en una lista.
        return list(self.session.exec(select(self.model)).all())

    # -----------------------------------------------------------------------
    # add
    # -----------------------------------------------------------------------
    def add(self, entity: T) -> T:
        """
        Inserta una entidad nueva en la tabla.

        ¿Por qué `flush()` y no `commit()`?
        ------------------------------------
        `flush()` ejecuta el SQL (INSERT) pero NO confirma la transacción.
        Eso le permite al UoW hacer `commit()` al final del bloque `with`
        y rollbackear si algo falla. Si hiciéramos commit() acá, no habría
        forma de deshacer.

        ¿Por qué `refresh()` después de `add()`?
        ----------------------------------------
        Para recargar campos que se generan en la DB (como el `id`
        autoincremental). Después de `refresh`, `entity.id` ya tiene el
        valor real asignado por la BD.
        """
        # `session.add(entity)` registra la entidad en la sesión (pending).
        self.session.add(entity)
        # `flush()` envía el SQL a la BD (INSERT ocurre).
        self.session.flush()
        # `refresh()` relee la entidad para tener valores generados por BD.
        self.session.refresh(entity)
        return entity

    # -----------------------------------------------------------------------
    # update
    # -----------------------------------------------------------------------
    def update(self, entity: T) -> T:
        """
        Actualiza una entidad existente.

        En SQLAlchemy/SQLModel, `session.add()` de una entidad con PK
        existente hace un UPDATE (no INSERT). Por eso el método es igual
        que `add`: agregar a la sesión + flush + refresh.
        """
        self.session.add(entity)
        self.session.flush()
        self.session.refresh(entity)
        return entity

    # -----------------------------------------------------------------------
    # delete
    # -----------------------------------------------------------------------
    def delete(self, entity: T) -> None:
        """
        Marca una entidad para eliminación.

        Como con `add`/`update`, solo flusheamos (no hacemos commit).
        El UoW decide al final si confirma o rollbackea.
        """
        # `session.delete(entity)` marca la fila para DELETE.
        self.session.delete(entity)
        # `flush()` ejecuta el SQL ahora. Sin flush, el delete queda
        # pendiente hasta el próximo flush automático o el commit.
        self.session.flush()
