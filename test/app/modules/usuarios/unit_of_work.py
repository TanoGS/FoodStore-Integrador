"""
Módulo: app/modules/usuarios/unit_of_work.py
==============================================

Unit of Work del módulo Usuarios. Expone el Repository de usuarios
sobre la misma sesión transaccional.

Patrón (siguiendo el modelo de referencia):
-------------------------------------------
El UoW se construye a partir de una session existente. En su __init__
crea el Repository (que también recibe la session) y lo expone como
atributo. El Service usa `with UsuarioUnitOfWork(self._session) as uow:`
para delimitar la transacción.
"""

from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.usuarios.repository import UsuarioRepository


class UsuarioUnitOfWork(UnitOfWork):
    """
    UoW específico de Usuarios. Expone `self.usuarios` (UsuarioRepository)
    construido sobre la misma session transaccional.
    """

    def __init__(self, session: Session) -> None:
        # Inicializamos la base (guarda la session).
        super().__init__(session)
        # Exponemos el Repository de usuarios. Usa la MISMA session.
        self.usuarios = UsuarioRepository(session)
