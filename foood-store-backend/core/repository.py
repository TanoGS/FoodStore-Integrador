from typing import Generic, TypeVar, Type, Sequence
from sqlmodel import Session, SQLModel, select

ModelT = TypeVar("ModelT", bound=SQLModel)


class BaseRepository(Generic[ModelT]):
    """
    Repositorio genérico que implementa operaciones CRUD básicas
    para cualquier modelo basado en SQLModel.

    Principio: el repositorio solo habla con la DB.
    No contiene lógica de negocio ni levanta HTTPException.

    Este repositorio sirve como clase base para repositorios específicos,
    donde se agregan queries más complejas o reglas de acceso particulares.
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

    def add(self, instance: ModelT) -> ModelT:
        """
        Persiste una entidad en la sesión.

        Flujo:
        - add(): marca la entidad para inserción/actualización
        - flush(): ejecuta el SQL sin commit (genera ID)
        - refresh(): sincroniza el estado del objeto con la DB

        Importante: NO hace commit. Esto lo maneja el UnitOfWork.
        """
        self.session.add(instance)
        self.session.flush()
        self.session.refresh(instance)
        return instance

    def delete(self, instance: ModelT) -> None:
        """
        Marca una entidad para eliminación física.

        Importante: NO hace commit. El UnitOfWork decide cuándo persistir.
        """
        self.session.delete(instance)
        self.session.flush()
