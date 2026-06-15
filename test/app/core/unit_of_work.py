"""
Módulo: app/core/unit_of_work.py
=================================

¿Qué hace este archivo?
------------------------
Define el **Unit of Work (UoW) genérico**. Es la clase que maneja la
**transacción** alrededor de una o más operaciones de Repository.

Recordatorio: patrón Unit of Work
----------------------------------
El UoW agrupa operaciones en una transacción. Al salir del bloque `with`:
  - Si todo OK → commit.
  - Si hubo excepción → rollback.
  - Siempre → close de la session.

Beneficios:
  - **Atomicidad**: si una operación falla, todas las anteriores se
    deshacen. No quedan "medios cambios".
  - **Testeable**: en tests podés verificar el estado entre operaciones
    (después de un add, antes del commit, etc.).
  - **Múltiples repositorios, una transacción**: `uow.usuarios` y
    `uow.productos` operan sobre la MISMA transacción.

Patrón del proyecto modelo:
---------------------------
El Service recibe la `session` en su `__init__`. Por CADA método de
negocio, hace `with UsuarioUnitOfWork(self._session) as uow:`. El UoW
se construye a partir de la session, expone los repos, y al salir
confirma o rollbackea.
"""

# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
# `Session` para el type hint del constructor.
from sqlmodel import Session


# ---------------------------------------------------------------------------
# CLASE: UnitOfWork (base)
# ---------------------------------------------------------------------------
class UnitOfWork:
    """
    Unit of Work genérico. Maneja commit/rollback/close automático.

    Esta clase base NO expone ningún repositorio. Las subclases
    (`UsuarioUnitOfWork`, `ProductoUnitOfWork`) lo hacen en su __init__.

    Ejemplo de uso (en un Service):
    -------------------------------
        class UsuarioService:
            def __init__(self, session: Session):
                self._session = session

            def register(self, payload):
                with UsuarioUnitOfWork(self._session) as uow:
                    # uow.usuarios es un UsuarioRepository ya listo.
                    if uow.usuarios.get_by_username(payload.username):
                        raise DuplicateResourceError(...)

                    usuario = Usuario(...)
                    uow.usuarios.add(usuario)
                    # al salir del with: commit automático
                    return UserPublic.model_validate(usuario)
                # si hubo excepción: rollback automático
    """

    def __init__(self, session: Session) -> None:
        """
        Args:
            session: la sesión ACTIVA (la creó el engine vía `get_session`).
                     El UoW NO la crea; solo la administra.
        """
        # La guardamos como "privada" (con _) para que las subclases no
        # la pisen por accidente. Las subclases exponen los REPOS, no la
        # session directamente.
        self._session = session

    # -----------------------------------------------------------------------
    # __enter__
    # -----------------------------------------------------------------------
    def __enter__(self) -> "UnitOfWork":
        """
        Al entrar al `with`, simplemente devolvemos self.

        NO abrimos transacción explícita: SQLAlchemy ya tiene una
        transacción implícita abierta en cada Session. El commit/rollback
        que hacemos en __exit__ actúa sobre ESA transacción.

        Devolver `self` permite hacer:
            with UoW() as uow:
                uow.mi_repo.add(...)
        """
        return self

    # -----------------------------------------------------------------------
    # __exit__
    # -----------------------------------------------------------------------
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Al salir del `with`:
          - Si NO hubo excepción (`exc_type is None`): COMMIT.
          - Si hubo excepción: ROLLBACK.
          - SIEMPRE: close de la session.

        ¿Por qué `try/finally`?
        -----------------------
        Para garantizar el `close()` incluso si el commit/rollback lanza.
        Si el commit falla (ej: constraint violation), queremos cerrar
        la session de todos modos para no leakear conexiones del pool.
        """
        try:
            if exc_type is None:
                # Todo OK → confirmamos la transacción.
                self._session.commit()
            else:
                # Hubo excepción → deshacemos TODO lo hecho dentro del with.
                self._session.rollback()
        finally:
            # SIEMPRE cerramos la session, haya habido excepción o no.
            # Esto libera la conexión al pool (o la cierra en SQLite).
            self._session.close()

    # -----------------------------------------------------------------------
    # commit explícito
    # -----------------------------------------------------------------------
    def commit(self) -> None:
        """
        Commit EXPLÍCITO dentro del `with`.

        Útil si querés persistir un cambio ANTES de salir del bloque.
        Ejemplo: querés que el id generado esté disponible inmediatamente
        para otra operación dentro del mismo with.

        ⚠️ En general no lo necesitás: el `__exit__` ya hace commit.
        """
        self._session.commit()

    # -----------------------------------------------------------------------
    # rollback explícito
    # -----------------------------------------------------------------------
    def rollback(self) -> None:
        """
        Rollback EXPLÍCITO dentro del `with`.

        Útil si querés abortar la transacción a propósito (no por una
        excepción, sino por una decisión de negocio).
        """
        self._session.rollback()
