from sqlmodel import Session


class UnitOfWork:
    """
    Gestiona el ciclo de vida de la transacción de base de datos.

    Uso en servicios:
        with uow:
            uow.categorias.add(categoria)
        # commit automático si no hay excepción
        # rollback automático si hay excepción

    El UoW es la única capa que llama a commit() y rollback().
    Los repositorios solo llaman a flush() para obtener IDs en memoria.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self._session.commit()
        else:
            self._session.rollback()
        self._session.close()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
