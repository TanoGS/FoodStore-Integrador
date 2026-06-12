from datetime import datetime, timezone
from typing import List, NamedTuple, Optional

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
from .schemas import (
    PedidoAdmin,
    DireccionResumida,
    DetallePedidoPublic,
)
from app.modules.catalogo.producto.models import Producto


# ---------------------------------------------------------------------------
# Labels legibles para formas de pago
# ---------------------------------------------------------------------------
_FORMA_PAGO_LABELS: dict[str, str] = {
    "EFECTIVO":      "Efectivo",
    "TRANSFERENCIA": "Transferencia",
    "MERCADOPAGO":   "MercadoPago",
}


# ---------------------------------------------------------------------------
# Resultado de un cambio de estado (para emitir por WebSocket)
# ---------------------------------------------------------------------------
class PedidoCambioResult(NamedTuple):
    pedido:    PedidoPublic
    historial: HistorialEstadoPublic


# ---------------------------------------------------------------------------
# Roles de STAFF con acceso a la gestión operativa de pedidos
# (ver todos, listar, cancelar sin restricción de estado, avanzar FSM)
# ---------------------------------------------------------------------------
_ROLES_STAFF_PEDIDOS = ("ADMIN", "GESTOR_PEDIDOS", "CAJERO", "COCINA")


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
    def crear_pedido(self, usuario_id: int, datos: PedidoCreate) -> PedidoCambioResult:
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

            # 3. Crear el pedido en estado PENDIENTE.
            #    El pedido pasa a CONFIRMADO únicamente cuando el webhook
            #    de MercadoPago notifica que el pago fue aprobado
            #    (ver procesar_webhook en app/modules/pagos/service.py).
            #    Este flujo permite:
            #    - Pagos online (MercadoPago) → PENDIENTE → CONFIRMADO (vía webhook)
            #    - Pagos manuales (Efectivo/Transferencia, futuro) → PENDIENTE → CONFIRMADO (vía cajero)
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
                motivo="Pedido creado - Esperando confirmación de pago",
            )
            uow.pedidos.add_historial(historial)

            # 6. Refrescar y retornar
            self._session.flush()
            self._session.refresh(pedido)
            self._session.refresh(historial)
            return PedidoCambioResult(
                pedido=PedidoPublic.model_validate(pedido),
                historial=HistorialEstadoPublic.model_validate(historial),
            )

    # ====================================================================
    # 2. AVANZAR ESTADO — STAFF (ADMIN / GESTOR_PEDIDOS / CAJERO / COCINA)
    # ====================================================================
    def avanzar_estado(
        self,
        pedido_id: int,
        datos: AvanzarEstadoRequest,
        actor_id: int,
    ) -> PedidoCambioResult:
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
            self._session.refresh(historial)
            return PedidoCambioResult(
                pedido=PedidoPublic.model_validate(pedido),
                historial=HistorialEstadoPublic.model_validate(historial),
            )

    # ====================================================================
    # 3. CANCELAR PEDIDO — CLIENTE O STAFF
    # ====================================================================
    def cancelar_pedido(
        self,
        pedido_id: int,
        motivo: str,
        usuario_id: int,
        roles: List[str],
    ) -> PedidoCambioResult:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_by_id_with_details(pedido_id)
            if not pedido:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pedido {pedido_id} no encontrado.",
                )

            es_privilegiado = self._es_staff(roles)

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
            self._session.refresh(historial)
            return PedidoCambioResult(
                pedido=PedidoPublic.model_validate(pedido),
                historial=HistorialEstadoPublic.model_validate(historial),
            )

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
            es_privilegiado = self._es_staff(roles)

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

            es_privilegiado = self._es_staff(roles)
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
    # 7. LISTAR TODOS PARA GESTIÓN (STAFF)
    # ====================================================================
    def obtener_todos_los_pedidos(self, offset: int = 0, limit: int = 20):
        """Obtiene todos los pedidos para panel de operación de staff."""
        with PedidoUnitOfWork(self._session) as uow:
            pedidos_orm = uow.pedidos.get_all_incluyendo_eliminados(offset, limit)
            total = uow.pedidos.count_total()
            pedidos_pydantic = [PedidoPublic.model_validate(p) for p in pedidos_orm]
            return {"data": pedidos_pydantic, "total": total}

    # ====================================================================
    # 8. MÉTODOS DE UTILIDAD (INTERNOS)
    # ====================================================================
    def _es_staff(self, roles: List[str]) -> bool:
        """
        Helper para verificar si el usuario tiene rol de staff operativo
        sobre pedidos (ADMIN, GESTOR_PEDIDOS, CAJERO, COCINA).
        """
        return any(r in roles for r in _ROLES_STAFF_PEDIDOS)

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

    def _construir_pedido_admin(self, pedido: Pedido) -> PedidoAdmin:
        """
        Construye un PedidoAdmin a partir de un pedido ORM,
        enriquecerlo con datos del usuario y la dirección.
        Si falla el enriquecimiento (usuario/dirección no existen),
        retorna datos de fallback en vez de crashear toda la lista.
        """
        usuario_nombre = f"Usuario #{pedido.usuario_id}"
        usuario_email  = ""
        direccion: Optional[DireccionResumida] = None

        try:
            from app.modules.usuario.models import Usuario
            from app.modules.direccion.models import DireccionEntrega

            usuario = self._session.get(Usuario, pedido.usuario_id)
            if usuario:
                usuario_nombre = getattr(usuario, 'nombre', None) or usuario_nombre
                usuario_email  = getattr(usuario, 'email',  '') or ''

            if pedido.direccion_id:
                dir_orm = self._session.get(DireccionEntrega, pedido.direccion_id)
                if dir_orm:
                    direccion = DireccionResumida(
                        calle=      getattr(dir_orm, 'calle',      None),
                        numero=     getattr(dir_orm, 'numero',     None),
                        ciudad=     getattr(dir_orm, 'ciudad',     None),
                        referencia= getattr(dir_orm, 'referencia',  None),
                    )
        except Exception:
            # Si falla el enriquecimiento, continuamos con datos parciales
            pass

        try:
            detalles = [
                DetallePedidoPublic.model_validate(d) for d in pedido.detalles
            ] if pedido.detalles else []
        except Exception:
            detalles = []

        return PedidoAdmin(
            id=pedido.id,
            usuario_id=pedido.usuario_id,
            usuario_nombre=usuario_nombre,
            usuario_email=usuario_email,
            direccion_id=pedido.direccion_id,
            direccion=direccion,
            estado_codigo=pedido.estado_codigo,
            forma_pago_codigo=pedido.forma_pago_codigo,
            forma_pago_label=_FORMA_PAGO_LABELS.get(
                pedido.forma_pago_codigo, pedido.forma_pago_codigo
            ),
            subtotal=pedido.subtotal,
            descuento=pedido.descuento,
            costo_envio=pedido.costo_envio,
            total=pedido.total,
            notas=pedido.notas,
            creado_en=pedido.creado_en,
            actualizado_en=pedido.actualizado_en,
            detalles=detalles,
        )

    # ====================================================================
    # 9. LISTAR PEDIDOS ADMIN (ENRIQUECIDOS) CON FILTRO DE PERÍODO
    # ====================================================================
    def obtener_todos_admin(
        self,
        periodo: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> dict:
        """
        Lista pedidos enriquecidos para el GestorPedidos.
        Incluye nombre/email del cliente, dirección completa y forma de pago
        en formato legible.

        Args:
            periodo: 'TODOS' | 'DIARIO' | 'MENSUAL' | None
            offset: desplazamiento para paginación
            limit: cantidad máxima de pedidos a devolver
        """
        with PedidoUnitOfWork(self._session) as uow:
            # Normalizar período
            periodo_norm = periodo if periodo in ('DIARIO', 'MENSUAL') else None

            pedidos_orm = uow.pedidos.get_all_incluyendo_eliminados_por_periodo(
                periodo_norm, offset, limit
            )
            total = uow.pedidos.count_total_por_periodo(periodo_norm)

            pedidos_admin = [self._construir_pedido_admin(p) for p in pedidos_orm]
            return {"data": pedidos_admin, "total": total}
