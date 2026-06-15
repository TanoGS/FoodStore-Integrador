"""
Módulo: app/modules/usuarios/repository.py
==========================================

Repository específico del módulo Usuarios.

Hereda de `BaseRepository[Usuario]` (CRUD base) y agrega queries
específicas del dominio: búsqueda por username, por email, listados
paginados, etc.

Patrón (modelo de referencia):
------------------------------
El Service obtiene la `session` una vez (de su constructor). El UoW
la envuelve en una transacción. El Repository opera sobre ESA session.

    Router → Service(session) → UsuarioUnitOfWork(session) → Repository(session)

NO se pasa `session` por parámetro a los métodos del Repository: usan
`self.session`. Esto simplifica las llamadas.
"""

# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
from sqlmodel import Session, func, select

from app.core.base_repository import BaseRepository
from app.modules.usuarios.models import Usuario


class UsuarioRepository(BaseRepository[Usuario]):
    """
    Repository de Usuario. CRUD base + queries de dominio.

    Hereda de `BaseRepository[Usuario]`:
      - get_by_id(id)
      - get_all()
      - add(entity)
      - update(entity)
      - delete(entity)

    Específicas:
      - get_by_username(username): para login y unicidad.
      - get_by_email(email): para unicidad y recuperación.
      - list_active(skip, limit): paginado de activos.
      - list_all(skip, limit): paginado de TODOS (admin).
      - count_active(): total de activos (para paginación).
    """

    def __init__(self, session: Session) -> None:
        # Llamamos al padre con la CLASE del modelo y la session.
        super().__init__(Usuario, session)

    # -----------------------------------------------------------------------
    # get_by_username
    # -----------------------------------------------------------------------
    def get_by_username(self, username: str) -> Usuario | None:
        """
        Busca un usuario por su username EXACTO (case-sensitive).

        Lo usan:
          - El Service en `register` (validar unicidad).
          - El Service en `authenticate` (login).
          - La dependency `get_current_user` (decodificar JWT).
        """
        statement = select(Usuario).where(Usuario.username == username)
        return self.session.exec(statement).first()

    # -----------------------------------------------------------------------
    # get_by_email
    # -----------------------------------------------------------------------
    def get_by_email(self, email: str) -> Usuario | None:
        """Busca un usuario por email exacto."""
        statement = select(Usuario).where(Usuario.email == email)
        return self.session.exec(statement).first()

    # -----------------------------------------------------------------------
    # list_active
    # -----------------------------------------------------------------------
    def list_active(self, skip: int = 0, limit: int = 100) -> list[Usuario]:
        """
        Lista usuarios ACTIVOS con paginación offset-based.

        Args:
            skip: cuántos registros saltar (para la página N).
            limit: tamaño de página (default 100, max recomendado 1000).
        """
        statement = (
            select(Usuario)
            .where(Usuario.is_active.is_(True))
            .order_by(Usuario.id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.exec(statement).all())

    # -----------------------------------------------------------------------
    # list_all
    # -----------------------------------------------------------------------
    def list_all(self, skip: int = 0, limit: int = 100) -> list[Usuario]:
        """
        Lista TODOS los usuarios (incluyendo desactivados).

        Para panel de admin. `order_by(id)` garantiza paginación estable
        (sin ORDER BY el orden es indefinido y podríamos repetir o
        saltar registros entre páginas).
        """
        statement = select(Usuario).order_by(Usuario.id).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

    # -----------------------------------------------------------------------
    # count_active
    # -----------------------------------------------------------------------
    def count_active(self) -> int:
        """
        Cuenta usuarios activos (para el `total` en paginación).

        ¿Por qué un SELECT COUNT separado y no `len(list_active(0, 999999))`?
        ---------------------------------------------------------------------
        Porque el COUNT usa índices y es O(1) o O(log N); traer 999999
        filas a memoria es O(N) en tiempo Y memoria. En tablas grandes,
        la diferencia es brutal.
        """
        statement = (
            select(func.count())
            .select_from(Usuario)
            .where(Usuario.is_active.is_(True))
        )
        return self.session.scalar(statement) or 0
