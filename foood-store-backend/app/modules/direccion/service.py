from datetime import datetime, timezone
from core.exceptions import NotFoundError, ForbiddenError, UnauthorizedError, BadRequestError, ConflictError, UnprocessableError, ServiceUnavailableError, BadGatewayError
from sqlmodel import Session

from .unit_of_work import DireccionUnitOfWork
from .models import DireccionEntrega
from .schemas import DireccionCreate, DireccionUpdate, DireccionPublic


class DireccionService:
    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------------------
    def agregar_direccion(self, usuario_id: int, datos: DireccionCreate) -> DireccionPublic:
        with DireccionUnitOfWork(self.session) as uow:
            previas = uow.direcciones.get_by_usuario(usuario_id)
            es_pred = datos.predeterminada or not previas
            if es_pred and previas:
                uow.direcciones.quitar_predeterminadas(usuario_id)
            nueva = DireccionEntrega(
                **datos.model_dump(exclude={"predeterminada"}),
                predeterminada=es_pred,
                usuario_id=usuario_id,
            )
            result = uow.direcciones.add(nueva)
            return DireccionPublic.model_validate(result)

    # ------------------------------------------------------------------
    def listar_mis_direcciones(self, usuario_id: int) -> list[DireccionPublic]:
        with DireccionUnitOfWork(self.session) as uow:
            return [DireccionPublic.model_validate(d) for d in uow.direcciones.get_by_usuario(usuario_id)]

    # ------------------------------------------------------------------
    def obtener_direccion(self, direccion_id: int, usuario_id: int) -> DireccionPublic:
        with DireccionUnitOfWork(self.session) as uow:
            d = uow.direcciones.get_by_id(direccion_id, usuario_id)
            if not d:
                raise NotFoundError("Dirección no encontrada.")
            return DireccionPublic.model_validate(d)

    # ------------------------------------------------------------------
    def actualizar_direccion(
        self, direccion_id: int, usuario_id: int, datos: DireccionUpdate
    ) -> DireccionPublic:
        with DireccionUnitOfWork(self.session) as uow:
            d = uow.direcciones.get_by_id(direccion_id, usuario_id)
            if not d:
                raise NotFoundError("Dirección no encontrada.")
            update_data = datos.model_dump(exclude_unset=True)
            if update_data.get("predeterminada"):
                uow.direcciones.quitar_predeterminadas(usuario_id)
            for key, value in update_data.items():
                setattr(d, key, value)
            d.actualizado_en = datetime.now(timezone.utc)
            result = uow.direcciones.add(d)
            return DireccionPublic.model_validate(result)

    # ------------------------------------------------------------------
    def marcar_principal(self, direccion_id: int, usuario_id: int) -> DireccionPublic:
        with DireccionUnitOfWork(self.session) as uow:
            d = uow.direcciones.get_by_id(direccion_id, usuario_id)
            if not d:
                raise NotFoundError("Dirección no encontrada.")
            uow.direcciones.quitar_predeterminadas(usuario_id)
            d.predeterminada = True
            d.actualizado_en = datetime.now(timezone.utc)
            result = uow.direcciones.add(d)
            return DireccionPublic.model_validate(result)

    # ------------------------------------------------------------------
    def eliminar_direccion(self, direccion_id: int, usuario_id: int) -> None:
        with DireccionUnitOfWork(self.session) as uow:
            d = uow.direcciones.get_by_id(direccion_id, usuario_id)
            if not d:
                raise NotFoundError("Dirección no encontrada.")
            if d.predeterminada:
                raise ConflictError(
                    "No podés eliminar la dirección principal. "
                    "Establecé otra dirección como principal antes de eliminar esta."
                )
            d.eliminado_en = datetime.now(timezone.utc)
            d.actualizado_en = datetime.now(timezone.utc)
            uow.direcciones.add(d)

    # ------------------------------------------------------------------
    def reactivar_direccion(self, direccion_id: int, usuario_id: int) -> DireccionPublic:
        with DireccionUnitOfWork(self.session) as uow:
            d = uow.direcciones.get_eliminado_by_id(direccion_id, usuario_id)
            if not d:
                raise NotFoundError("Dirección no encontrada o no está eliminada.")
            d.eliminado_en = None
            d.actualizado_en = datetime.now(timezone.utc)
            result = uow.direcciones.add(d)
            return DireccionPublic.model_validate(result)
