from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from .models import (
    EstadoPedido,
    HistorialEstadoPedido,
    DetallePedido,
    Pedido,
)
from .schemas import AvanzarEstadoRequest, PedidoCreate
from .unit_of_work import PedidoUnitOfWork
from app.modules.catalogo.producto.models import Producto


# ---------------------------------------------------------------------------
# Mapa FSM: estado_actual → estados permitidos
# ---------------------------------------------------------------------------
_FSM: dict[str, list[str]] = {
    EstadoPedido.PENDIENTE:      [EstadoPedido.CONFIRMADO,     EstadoPedido.CANCELADO],
    EstadoPedido.CONFIRMADO:     [EstadoPedido.EN_PREPARACION, EstadoPedido.CANCELADO],
    EstadoPedido.EN_PREPARACION: [EstadoPedido.EN_CAMINO,      EstadoPedido.CANCELADO],
    EstadoPedido.EN_CAMINO:      [EstadoPedido.ENTREGADO],
    EstadoPedido.ENTREGADO:      [],
    EstadoPedido.CANCELADO:      [],
}

# Estados desde los que un CLIENTE puede auto-cancelar
_CANCELACION_CLIENTE = {EstadoPedido.PENDIENTE, EstadoPedido.CONFIRMADO}


class PedidoService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -----------------------------------------------------------------------
    # Crear pedido — transacción atómica (Unit of Work manual)
    # -----------------------------------------------------------------------
    def crear_pedido(self, usuario_id: int, datos: PedidoCreate) -> Pedido:
        subtotal = 0.0
        detalles: list[DetallePedido] = []

        # 1. Validar productos y construir snapshots (precio + nombre congelados)
        for item in datos.detalles:
            producto = self._session.get(Producto, item.producto_id)
            if not producto or not producto.activo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Producto {item.producto_id} no disponible.",
                )
            precio = float(producto.precio)
            sub    = round(precio * item.cantidad, 2)
            subtotal += sub
            detalles.append(
                DetallePedido(
                    producto_id=item.producto_id,
                    cantidad=item.cantidad,
                    nombre_snapshot=producto.nombre,
                    precio_snapshot=precio,
                    subtotal_snap=sub,
                    personalizacion=item.personalizacion,
                )
            )

        descuento   = 0.0
        costo_envio = 50.0
        total       = round(subtotal - descuento + costo_envio, 2)

        pedido = Pedido(
            usuario_id=usuario_id,
            direccion_id=datos.direccion_id,
            estado_codigo=EstadoPedido.PENDIENTE,
            forma_pago_codigo=datos.forma_pago_codigo,
            subtotal=subtotal,
            descuento=descuento,
            costo_envio=costo_envio,
            total=total,
            notas=datos.notas,
        )

        uow = PedidoUnitOfWork(self._session)
        try:
            # 2. Flush para obtener pedido.id antes del commit
            self._session.add(pedido)
            self._session.flush()

            # 3. Persistir detalles con FK al pedido ya creado
            for d in detalles:
                d.pedido_id = pedido.id
                self._session.add(d)

            # 4. Audit Trail — primer registro (RN-02: estado_desde = NULL)
            self._session.add(
                HistorialEstadoPedido(
                    pedido_id=pedido.id,
                    estado_desde=None,
                    estado_hacia=EstadoPedido.PENDIENTE,
                    usuario_id=usuario_id,
                    motivo="Creación del pedido",
                )
            )

            uow.commit()
            self._session.refresh(pedido)
            return pedido

        except Exception:
            uow.rollback()
            raise

    # -----------------------------------------------------------------------
    # Avanzar estado — solo ADMIN / GESTOR_PEDIDOS
    # Validación FSM en la capa de servicio, nunca en el router
    # -----------------------------------------------------------------------
    def avanzar_estado(
        self,
        pedido_id: int,
        datos: AvanzarEstadoRequest,
        actor_id: int,
    ) -> Pedido:
        pedido = self._get_o_404(pedido_id)
        estado_actual = pedido.estado_codigo
        estado_nuevo  = datos.estado_hacia.value

        # Validar transición en el mapa FSM
        permitidos = [e.value for e in _FSM.get(estado_actual, [])]
        if estado_nuevo not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Transición inválida: {estado_actual} → {estado_nuevo}.",
            )

        # RN-05: motivo obligatorio al cancelar
        if estado_nuevo == EstadoPedido.CANCELADO and not datos.motivo:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El motivo es obligatorio al cancelar.",
            )

        uow = PedidoUnitOfWork(self._session)
        try:
            pedido.estado_codigo  = estado_nuevo
            pedido.actualizado_en = datetime.now(timezone.utc)
            self._session.add(pedido)
            self._session.add(
                HistorialEstadoPedido(
                    pedido_id=pedido.id,
                    estado_desde=estado_actual,
                    estado_hacia=estado_nuevo,
                    usuario_id=actor_id,
                    motivo=datos.motivo,
                )
            )
            uow.commit()
            self._session.refresh(pedido)
            return pedido

        except Exception:
            uow.rollback()
            raise

    # -----------------------------------------------------------------------
    # Cancelar pedido — disponible al propio cliente (restricción de estado)
    # -----------------------------------------------------------------------
    def cancelar_pedido(
        self,
        pedido_id: int,
        motivo: str,
        usuario_id: int,
        roles: list[str],
    ) -> Pedido:
        pedido = self._get_o_404(pedido_id)

        es_privilegiado = any(r in roles for r in ("ADMIN", "GESTOR_PEDIDOS"))

        # Verificar propiedad del pedido para clientes
        if not es_privilegiado and pedido.usuario_id != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para cancelar este pedido.",
            )

        estado_actual = pedido.estado_codigo

        # Clientes solo pueden cancelar desde PENDIENTE o CONFIRMADO
        if not es_privilegiado and estado_actual not in {e.value for e in _CANCELACION_CLIENTE}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Solo puedes cancelar desde PENDIENTE o CONFIRMADO. Estado actual: {estado_actual}.",
            )

        # Verificar que el FSM permite cancelar desde este estado
        if EstadoPedido.CANCELADO.value not in [e.value for e in _FSM.get(estado_actual, [])]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"No se puede cancelar desde el estado {estado_actual}.",
            )

        uow = PedidoUnitOfWork(self._session)
        try:
            pedido.estado_codigo  = EstadoPedido.CANCELADO
            pedido.actualizado_en = datetime.now(timezone.utc)
            self._session.add(pedido)
            self._session.add(
                HistorialEstadoPedido(
                    pedido_id=pedido.id,
                    estado_desde=estado_actual,
                    estado_hacia=EstadoPedido.CANCELADO,
                    usuario_id=usuario_id,
                    motivo=motivo,
                )
            )
            uow.commit()
            self._session.refresh(pedido)
            return pedido

        except Exception:
            uow.rollback()
            raise

    # -----------------------------------------------------------------------
    # Listado — CLIENT ve solo sus pedidos; ADMIN/GESTOR_PEDIDOS ven todos
    # -----------------------------------------------------------------------
    def listar_pedidos(self, usuario_id: int, roles: list[str]) -> List[Pedido]:
        stmt = (
            select(Pedido)
            .options(selectinload(Pedido.detalles))
        )
        if not any(r in roles for r in ("ADMIN", "GESTOR_PEDIDOS")):
            stmt = stmt.where(Pedido.usuario_id == usuario_id)
        stmt = stmt.order_by(Pedido.creado_en.desc())
        return list(self._session.exec(stmt).all())

    # -----------------------------------------------------------------------
    # Obtener pedido individual con control de acceso
    # -----------------------------------------------------------------------
    def obtener_pedido(self, pedido_id: int, usuario_id: int, roles: list[str]) -> Pedido:
        pedido = self._get_o_404(pedido_id)
        es_privilegiado = any(r in roles for r in ("ADMIN", "GESTOR_PEDIDOS"))
        if not es_privilegiado and pedido.usuario_id != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver este pedido.",
            )
        return pedido

    # -----------------------------------------------------------------------
    # Historial de transiciones ordenado por fecha (RN-03)
    # -----------------------------------------------------------------------
    def obtener_historial(
        self, pedido_id: int, usuario_id: int, roles: list[str]
    ) -> List[HistorialEstadoPedido]:
        pedido = self.obtener_pedido(pedido_id, usuario_id, roles)
        stmt = (
            select(HistorialEstadoPedido)
            .where(HistorialEstadoPedido.pedido_id == pedido.id)
            .order_by(HistorialEstadoPedido.creado_en.asc())
        )
        return list(self._session.exec(stmt).all())

    # -----------------------------------------------------------------------
    # Helper privado
    # -----------------------------------------------------------------------
    def _get_o_404(self, pedido_id: int) -> Pedido:
        pedido = self._session.exec(
            select(Pedido)
            .options(selectinload(Pedido.detalles))
            .where(Pedido.id == pedido_id)
        ).first()
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido {pedido_id} no encontrado.",
            )
        return pedido
