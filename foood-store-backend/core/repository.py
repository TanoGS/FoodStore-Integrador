from typing import Generic, TypeVar, Type, Sequence, Any
from datetime import datetime, timezone
from sqlmodel import Session, SQLModel, select

ModelT = TypeVar("ModelT", bound=SQLModel)


class BaseRepository(Generic[ModelT]):
    """
    Repositorio genérico con operaciones CRUD base para cualquier modelo SQLModel.
    """

    def __init__(self, session: Session, model: Type[ModelT]) -> None:
        self.session = session
        self.model = model

    def get_by_id(self, record_id: int) -> ModelT | None:
        return self.session.get(self.model, record_id)

    def get_all(self, offset: int = 0, limit: int = 20) -> Sequence[ModelT]:
        return self.session.exec(
            select(self.model).offset(offset).limit(limit)
        ).all()

    def count(self) -> int:
        """
        Devuelve el total de registros de la tabla.
        Útil para construir respuestas paginadas sin cargar todas las filas.

        NO hace commit. Solo lectura.
        """
        from sqlalchemy import func
        result = self.session.exec(
            select(func.count()).select_from(self.model)  # type: ignore[arg-type]
        )
        return result.one()

    def add(self, instance: ModelT) -> ModelT:
        """
        Persiste una entidad en la sesión.

        Flujo:
        - add(): marca la entidad para inserción/actualización.
        - flush(): ejecuta el SQL sin commit (genera ID).
        - refresh(): sincroniza el estado del objeto con la DB.

        NO hace commit. Esto lo maneja el UnitOfWork.
        """
        self.session.add(instance)
        self.session.flush()
        self.session.refresh(instance)
        return instance

    def soft_delete(self, instance: ModelT) -> None:
        """
        Marca lógicamente una entidad como eliminada.

        Asigna la hora UTC actual al primer campo cuyo nombre sea
        'eliminado_en' o 'deleted_at' que encuentre en el modelo.
        Si el modelo no tiene ninguno de esos campos, lanza AttributeError.

        NO hace commit. El UnitOfWork decide cuándo persistir.
        """
        _SOFT_DELETE_FIELDS = ("eliminado_en", "deleted_at")
        for field_name in _SOFT_DELETE_FIELDS:
            if hasattr(instance, field_name):
                setattr(instance, field_name, datetime.now(timezone.utc))
                self.session.add(instance)
                self.session.flush()
                return
        raise AttributeError(
            f"{type(instance).__name__} no tiene campo de soft-delete "
            f"({', '.join(_SOFT_DELETE_FIELDS)})."
        )

    def delete(self, instance: ModelT) -> None:
        """
        Elimina físicamente una entidad (hard delete).

        Usar solo cuando el modelo no tiene soft-delete o cuando
        se requiera purgar datos de forma permanente.

        NO hace commit. El UnitOfWork decide cuándo persistir.
        """
        self.session.delete(instance)
        self.session.flush()
