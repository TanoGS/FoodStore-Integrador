from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlmodel import Session, select

from .models import (
    EstadoPedido,
    HistorialEstadoPedido,
    DetallePedido,
    Pedido,
)
from .schemas import (
    AvanzarEstadoRequest,
    PedidoCreate,
    PedidoPublic,
    HistorialEstadoPublic,
)
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

    # ====================================================================
    # 1. CREAR PEDIDO — TRANSACCIÓN ATÓMICA CON UNIT OF WORK
    # ====================================================================
    def crear_pedido(self, usuario_id: int, datos: PedidoCreate) -> PedidoPublic:
        with PedidoUnitOfWork(self._session) as uow:
            # 1. Validar productos y construir snapshots (precio + nombre congelados)
            detalles: List[DetallePedido] = []
            subtotal = 0.0

            for item in datos.detalles:
                producto = self._session.get(Producto, item.producto_id)
                if not producto or not producto.activo:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Producto {item.producto_id} no disponible.",
                    )
                
                precio = float(producto.precio)
                sub = round(precio * item.cantidad, 2)
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

            # 2. Calcular totales
            descuento = 0.0
            costo_envio = 50.0
            total = round(subtotal - descuento + costo_envio, 2)

            # 3. Crear el pedido
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

            uow.pedidos.add(pedido)

            # 4. Asignar FK y persistir detalles
            for d in detalles:
                d.pedido_id = pedido.id
            uow.pedidos.add_many_detalles(detalles)

            # 5. Audit Trail — primer registro (RN-02: estado_desde = NULL)
            historial = HistorialEstadoPedido(
                pedido_id=pedido.id,
                estado_desde=None,
                estado_hacia=EstadoPedido.PENDIENTE,
                usuario_id=usuario_id,
                motivo="Creación del pedido",
            )
            uow.pedidos.add_historial(historial)

            # 6. Refrescar y retornar
            self._session.flush()
            self._session.refresh(pedido)
            return PedidoPublic.model_validate(pedido)

    # ====================================================================
    # 2. AVANZAR ESTADO — SOLO ADMIN / GESTOR_PEDIDOS
    # ====================================================================
    def avanzar_estado(
        self,
        pedido_id: int,
        datos: AvanzarEstadoRequest,
        actor_id: int,
    ) -> PedidoPublic:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_by_id_with_details(pedido_id)
            if not pedido:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pedido {pedido_id} no encontrado.",
                )

            estado_actual = pedido.estado_codigo
            estado_nuevo = datos.estado_hacia.value

            # Validar transición FSM
            permitidos = [e.value for e in _FSM.get(estado_actual, [])]
            if estado_nuevo not in permitidos:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Transición inválida: {estado_actual} → {estado_nuevo}.",
                )

            # RN-05: motivo obligatorio al cancelar
            if estado_nuevo == EstadoPedido.CANCELADO.value and not datos.motivo:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="El motivo es obligatorio al cancelar.",
                )

            # Actualizar estado y persistir
            pedido.estado_codigo = estado_nuevo
            pedido.actualizado_en = datetime.now(timezone.utc)
            uow.pedidos.add(pedido)

            # Registrar en historial
            historial = HistorialEstadoPedido(
                pedido_id=pedido.id,
                estado_desde=estado_actual,
                estado_hacia=estado_nuevo,
                usuario_id=actor_id,
                motivo=datos.motivo,
            )
            uow.pedidos.add_historial(historial)

            self._session.flush()
            self._session.refresh(pedido)
            return PedidoPublic.model_validate(pedido)

    # ====================================================================
    # 3. CANCELAR PEDIDO — CLIENTE O STAFF
    # ====================================================================
    def cancelar_pedido(
        self,
        pedido_id: int,
        motivo: str,
        usuario_id: int,
        roles: List[str],
    ) -> PedidoPublic:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_by_id_with_details(pedido_id)
            if not pedido:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pedido {pedido_id} no encontrado.",
                )

            es_privilegiado = any(r in roles for r in ("ADMIN", "GESTOR_PEDIDOS"))

            # Verificar propiedad del pedido para clientes
            if not es_privilegiado and pedido.usuario_id != usuario_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para cancelar este pedido.",
                )

            estado_actual = pedido.estado_codigo

            # Clientes solo pueden cancelar desde PENDIENTE o CONFIRMADO
            if not es_privilegiado:
                estados_cancelables = {e.value for e in _CANCELACION_CLIENTE}
                if estado_actual not in estados_cancelables:
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

            # Actualizar estado
            pedido.estado_codigo = EstadoPedido.CANCELADO
            pedido.actualizado_en = datetime.now(timezone.utc)
            uow.pedidos.add(pedido)

            # Registrar historial
            historial = HistorialEstadoPedido(
                pedido_id=pedido.id,
                estado_desde=estado_actual,
                estado_hacia=EstadoPedido.CANCELADO,
                usuario_id=usuario_id,
                motivo=motivo,
            )
            uow.pedidos.add_historial(historial)

            self._session.flush()
            self._session.refresh(pedido)
            return PedidoPublic.model_validate(pedido)

    # ====================================================================
    # 4. LISTAR PEDIDOS — PAGINADO
    # ====================================================================
    def listar_pedidos(
        self,
        usuario_id: int,
        roles: List[str],
        offset: int = 0,
        limit: int = 20,
        estado: Optional[str] = None,
    ):
        with PedidoUnitOfWork(self._session) as uow:
            es_privilegiado = any(r in roles for r in ("ADMIN", "GESTOR_PEDIDOS"))

            if es_privilegiado:
                if estado:
                    pedidos_orm = uow.pedidos.get_all_activos_por_estado(estado, offset, limit)
                    total = uow.pedidos.count_activos_por_estado(estado)
                else:
                    pedidos_orm = uow.pedidos.get_all_activos(offset, limit)
                    total = uow.pedidos.count_activos()
            else:
                pedidos_orm = uow.pedidos.get_all_activos_por_usuario(usuario_id, offset, limit)
                total = uow.pedidos.count_activos_por_usuario(usuario_id)

            pedidos_pydantic = [PedidoPublic.model_validate(p) for p in pedidos_orm]
            return {"data": pedidos_pydantic, "total": total}

    # ====================================================================
    # 5. OBTENER PEDIDO INDIVIDUAL
    # ====================================================================
    def obtener_pedido(
        self,
        pedido_id: int,
        usuario_id: int,
        roles: List[str],
    ) -> PedidoPublic:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_by_id_with_details(pedido_id)
            if not pedido:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pedido {pedido_id} no encontrado.",
                )

            es_privilegiado = any(r in roles for r in ("ADMIN", "GESTOR_PEDIDOS"))
            if not es_privilegiado and pedido.usuario_id != usuario_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para ver este pedido.",
                )

            return PedidoPublic.model_validate(pedido)

    # ====================================================================
    # 6. OBTENER HISTORIAL DE UN PEDIDO
    # ====================================================================
    def obtener_historial(
        self,
        pedido_id: int,
        usuario_id: int,
        roles: List[str],
    ) -> List[HistorialEstadoPublic]:
        # Primero verificamos acceso al pedido
        self.obtener_pedido(pedido_id, usuario_id, roles)

        with PedidoUnitOfWork(self._session) as uow:
            historiales = uow.pedidos.get_historial_by_pedido(pedido_id)
            return [HistorialEstadoPublic.model_validate(h) for h in historiales]

    # ====================================================================
    # 7. LISTAR TODOS PARA GESTIÓN (ADMIN)
    # ====================================================================
    def obtener_todos_los_pedidos(self, offset: int = 0, limit: int = 20):
        """Obtiene todos los pedidos para panel de administración."""
        with PedidoUnitOfWork(self._session) as uow:
            pedidos_orm = uow.pedidos.get_all_incluyendo_eliminados(offset, limit)
            total = uow.pedidos.count_total()
            pedidos_pydantic = [PedidoPublic.model_validate(p) for p in pedidos_orm]
            return {"data": pedidos_pydantic, "total": total}

    # ====================================================================
    # 8. MÉTODOS DE UTILIDAD (INTERNOS)
    # ====================================================================
    def _es_staff(self, roles: List[str]) -> bool:
        """Helper para verificar si el usuario tiene rol de staff."""
        return any(r in roles for r in ("ADMIN", "GESTOR_PEDIDOS"))

    def _verificar_acceso_pedido(
        self,
        pedido: Pedido,
        usuario_id: int,
        roles: List[str],
    ) -> None:
        """Verifica que el usuario tenga acceso al pedido."""
        if self._es_staff(roles):
            return
        if pedido.usuario_id != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para acceder a este pedido.",
            )