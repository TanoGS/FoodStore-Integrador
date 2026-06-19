from datetime import datetime, timezone
from typing import Dict, List, NamedTuple, Optional

from sqlmodel import Session

from core.exceptions import (
    NotFoundError, ForbiddenError, BadRequestError, UnprocessableError
)

from .models import (
    EstadoPedido,
    HistorialEstadoPedido,
    DetallePedido,
    Pedido,
    TipoEntrega,
)
from .schemas import (
    AvanzarEstadoRequest,
    PedidoCreate,
    PedidoPublic,
    HistorialEstadoPublic,
    _TIPO_ENTREGA_LABELS,
)
from .unit_of_work import PedidoUnitOfWork
from .schemas import (
    PedidoAdmin,
    DireccionResumida,
    DetallePedidoPublic,
)
from .events import (
    ROOM_STAFF_PEDIDOS,
    room_user,
    serialize_pedido_creado,
    serialize_pedido_estado_cambiado,
    serialize_pedido_mio_actualizado,
    serialize_stock_alerta,
)
from .ws_manager import ws_manager
from app.modules.catalogo.producto.repository import ProductoRepository
from app.modules.pedido import stock as _stock
from app.modules.usuario.repository import UsuarioRepository
from app.modules.direccion.repository import DireccionRepository
from core.settings_runtime import get_costo_envio_delivery


# ---------------------------------------------------------------------------
# Labels legibles para formas de pago
# ---------------------------------------------------------------------------
_FORMA_PAGO_LABELS: dict[str, str] = {
    "EFECTIVO":    "Efectivo",
    "MERCADOPAGO": "MercadoPago",
}


# ---------------------------------------------------------------------------
# Resultado de un cambio de estado (para emitir por WebSocket)
# ---------------------------------------------------------------------------
class PedidoCambioResult(NamedTuple):
    pedido:           PedidoPublic
    historial:        HistorialEstadoPublic
    stock_bajo:       Optional[List[dict]] = None


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
    EstadoPedido.EN_CAMINO:      [EstadoPedido.ENTREGADO,      EstadoPedido.CANCELADO],
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
    async def crear_pedido(self, usuario_id: int, datos: PedidoCreate) -> PedidoCambioResult:
        # ── Validar stock ANTES de iniciar la transacción ──────────────────
        # Se construye una preview del pedido sin persistir nada.
        # Si falta stock, se lanza un error 400 antes de entrar al UoW.
        # El mensaje de detalle va en el response para debugging/admin;
        # el frontend del cliente muestra un mensaje genérico al usuario.
        faltantes_stock = _stock.obtener_resumen_stock_preview(self._session, datos)
        if faltantes_stock:
            raise BadRequestError({
                    "error": "stock_insuficiente",
                    "faltantes": faltantes_stock,
                })

        with PedidoUnitOfWork(self._session) as uow:
            # 1. Validar productos y construir snapshots
            detalles, subtotal, nombres_por_producto = self._construir_detalles(datos)

            # 2. Calcular totales
            descuento = 0.0
            # El costo de envío aplica SOLO para delivery (valor configurable desde el panel)
            costo_envio = get_costo_envio_delivery() if datos.tipo_entrega == TipoEntrega.DELIVERY else 0.0
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
                tipo_entrega=datos.tipo_entrega.value,
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

            # Construir la respuesta Pydantic y enriquecer con los nombres
            # de ingredientes removidos usando el mapa temporal.
            response = PedidoPublic.model_validate(pedido)
            for detalle_pyd in response.detalles:
                detalle_pyd.personalizacion_nombres = nombres_por_producto.get(
                    detalle_pyd.producto_id
                )

            result = PedidoCambioResult(
                pedido=response,
                historial=HistorialEstadoPublic.model_validate(historial),
            )

        # RN-06: broadcast DESPUÉS del commit (fuera del bloque UoW)
        await ws_manager.broadcast(
            ROOM_STAFF_PEDIDOS,
            serialize_pedido_creado(result.pedido),
        )
        await ws_manager.broadcast(
            room_user(result.pedido.usuario_id),
            serialize_pedido_mio_actualizado(
                id_=result.pedido.id,
                estado_codigo=result.pedido.estado_codigo,
                actualizado_en=(
                    result.pedido.actualizado_en.isoformat()
                    if result.pedido.actualizado_en
                    else result.pedido.creado_en.isoformat()
                ),
            ),
        )
        return result

    # ====================================================================
    # 2. AVANZAR ESTADO — STAFF (ADMIN / GESTOR_PEDIDOS / CAJERO / COCINA)
    # ====================================================================
    async def avanzar_estado(
        self,
        pedido_id: int,
        datos: AvanzarEstadoRequest,
        actor_id: int,
    ) -> PedidoCambioResult:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_by_id_with_details(pedido_id)
            if not pedido:
                raise NotFoundError(f"Pedido {pedido_id} no encontrado.")

            estado_actual = pedido.estado_codigo
            estado_nuevo = datos.estado_hacia.value

            # Validar transición FSM
            permitidos = [e.value for e in _FSM.get(estado_actual, [])]
            if estado_nuevo not in permitidos:
                raise UnprocessableError(f"Transición inválida: {estado_actual} → {estado_nuevo}.")

            # RN-05: motivo obligatorio al cancelar
            if estado_nuevo == EstadoPedido.CANCELADO.value and not datos.motivo:
                raise UnprocessableError("El motivo es obligatorio al cancelar.")

            # Descontar stock al confirmar el pedido y detectar alerta
            stock_bajo: Optional[List[dict]] = None
            if estado_nuevo == EstadoPedido.CONFIRMADO.value:
                cambios = _stock.descontar_stock(self._session, pedido)
                stock_bajo = _stock.detectar_stock_bajo(self._session, cambios)

            # Devolver stock si se cancela desde un estado donde ya se había descontado
            # (el stock se descuenta al confirmar, por eso excluimos PENDIENTE)
            if estado_nuevo == EstadoPedido.CANCELADO.value and estado_actual != EstadoPedido.PENDIENTE.value:
                _stock.devolver_stock(self._session, pedido)

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
            response = PedidoPublic.model_validate(pedido)
            self._enriquecer_personalizaciones([response])
            result = PedidoCambioResult(
                pedido=response,
                historial=HistorialEstadoPublic.model_validate(historial),
                stock_bajo=stock_bajo,
            )

        # RN-06: broadcast DESPUÉS del commit
        await ws_manager.broadcast(
            ROOM_STAFF_PEDIDOS,
            serialize_pedido_estado_cambiado(
                pedido=result.pedido,
                estado_desde=result.historial.estado_desde,
                estado_hacia=result.historial.estado_hacia,
                usuario_actor_id=result.historial.usuario_id,
                motivo=result.historial.motivo,
                historial=result.historial,
            ),
        )
        await ws_manager.broadcast(
            room_user(result.pedido.usuario_id),
            serialize_pedido_mio_actualizado(
                id_=result.pedido.id,
                estado_codigo=result.pedido.estado_codigo,
                actualizado_en=(
                    result.pedido.actualizado_en.isoformat()
                    if result.pedido.actualizado_en
                    else None
                ),
            ),
        )
        if result.stock_bajo:
            await ws_manager.broadcast(
                ROOM_STAFF_PEDIDOS,
                serialize_stock_alerta(result.stock_bajo),
            )
        return result

    # ====================================================================
    # 3. CANCELAR PEDIDO — CLIENTE O STAFF
    # ====================================================================
    async def cancelar_pedido(
        self,
        pedido_id: int,
        motivo: str,
        usuario_id: int,
        roles: List[str],
    ) -> PedidoCambioResult:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_by_id_with_details(pedido_id)
            if not pedido:
                raise NotFoundError(f"Pedido {pedido_id} no encontrado.")

            es_privilegiado = self._es_staff(roles)

            # Verificar propiedad del pedido para clientes
            if not es_privilegiado and pedido.usuario_id != usuario_id:
                raise ForbiddenError("No tienes permiso para cancelar este pedido.")

            estado_actual = pedido.estado_codigo

            # Clientes solo pueden cancelar desde PENDIENTE o CONFIRMADO
            if not es_privilegiado:
                estados_cancelables = {e.value for e in _CANCELACION_CLIENTE}
                if estado_actual not in estados_cancelables:
                    raise UnprocessableError(f"Solo puedes cancelar desde PENDIENTE o CONFIRMADO. Estado actual: {estado_actual}.")

            # Verificar que el FSM permite cancelar desde este estado
            if EstadoPedido.CANCELADO.value not in [e.value for e in _FSM.get(estado_actual, [])]:
                raise UnprocessableError(f"No se puede cancelar desde el estado {estado_actual}.")

            # Devolver stock si el pedido ya estaba confirmado
            # (stock solo se descuenta al pasar a CONFIRMADO)
            if estado_actual != EstadoPedido.PENDIENTE.value:
                _stock.devolver_stock(self._session, pedido)

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
            response = PedidoPublic.model_validate(pedido)
            self._enriquecer_personalizaciones([response])
            result = PedidoCambioResult(
                pedido=response,
                historial=HistorialEstadoPublic.model_validate(historial),
            )

        # RN-06: broadcast DESPUÉS del commit
        await ws_manager.broadcast(
            ROOM_STAFF_PEDIDOS,
            serialize_pedido_estado_cambiado(
                pedido=result.pedido,
                estado_desde=result.historial.estado_desde,
                estado_hacia=result.historial.estado_hacia,
                usuario_actor_id=result.historial.usuario_id,
                motivo=result.historial.motivo,
                historial=result.historial,
            ),
        )
        await ws_manager.broadcast(
            room_user(result.pedido.usuario_id),
            serialize_pedido_mio_actualizado(
                id_=result.pedido.id,
                estado_codigo=result.pedido.estado_codigo,
                actualizado_en=(
                    result.pedido.actualizado_en.isoformat()
                    if result.pedido.actualizado_en
                    else None
                ),
            ),
        )
        return result

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
            self._enriquecer_personalizaciones(pedidos_pydantic)
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
                raise NotFoundError(f"Pedido {pedido_id} no encontrado.")

            es_privilegiado = self._es_staff(roles)
            if not es_privilegiado and pedido.usuario_id != usuario_id:
                raise ForbiddenError("No tienes permiso para ver este pedido.")

            response = PedidoPublic.model_validate(pedido)
            self._enriquecer_personalizaciones([response])
            return response

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
            self._enriquecer_personalizaciones(pedidos_pydantic)
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

    def _construir_detalles(
        self,
        datos: "PedidoCreate",
    ) -> "tuple[List[DetallePedido], float, Dict[int, List[str]]]":
        """
        Construye los objetos `DetallePedido` a partir del request.

        Valida:
        - Que cada producto exista y esté activo.
        - Que las personalizaciones solo incluyan ingredientes del producto y
          que esos ingredientes sean removibles.

        Retorna:
        - detalles: lista de DetallePedido (sin pedido_id — se asigna después del flush)
        - subtotal: suma de subtotales de cada ítem
        - nombres_por_producto: mapa producto_id → nombres de ingredientes removidos
          (para enriquecer la respuesta Pydantic sin persistir en BD)
        """
        detalles: List[DetallePedido] = []
        subtotal = 0.0
        nombres_por_producto: Dict[int, List[str]] = {}

        for item in datos.detalles:
            producto = ProductoRepository(self._session).get_by_id(item.producto_id)
            if not producto or not producto.activo:
                raise NotFoundError(f"Producto {item.producto_id} no disponible.")

            ingredientes_producto: Dict[int, object] = {}
            if item.personalizacion:
                ingredientes_producto = {
                    e.ingrediente_id: e for e in producto.ingredientes_enlaces
                }
                for ing_id in item.personalizacion:
                    enlace = ingredientes_producto.get(ing_id)
                    if enlace is None:
                        raise BadRequestError(
                            f"El ingrediente {ing_id} no pertenece al producto."
                        )
                    if not enlace.es_removible:  # type: ignore[attr-defined]
                        nombre = getattr(enlace.ingrediente, "nombre", str(ing_id))  # type: ignore[attr-defined]
                        raise BadRequestError(f"El ingrediente '{nombre}' no es removible.")

            precio = float(producto.precio)
            sub = round(precio * item.cantidad, 2)
            subtotal += sub

            if item.personalizacion:
                nombres_removidos = [
                    ingredientes_producto[pid].ingrediente.nombre  # type: ignore[attr-defined]
                    for pid in item.personalizacion
                    if pid in ingredientes_producto
                ]
                if nombres_removidos:
                    nombres_por_producto[item.producto_id] = nombres_removidos

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

        return detalles, subtotal, nombres_por_producto

    # ====================================================================
    # 10. HELPER: ENRIQUECER PERSONALIZACIONES CON NOMBRES LEGIBLES
    # ====================================================================
    def _enriquecer_personalizaciones(self, pedidos: List[PedidoPublic]) -> None:
        """
        Para cada detalle de cada pedido, resuelve los IDs de personalizacion
        a nombres legibles consultando Producto + ProductoIngrediente.
        Modifica in-place el campo personalizacion_nombres de cada DetallePedidoPublic.

        Se aplica a TODOS los endpoints que devuelven PedidoPublic para que
        la cocina y cualquier otra vista puedan mostrar 'Sin: Cebolla, Tomate'
        en lugar de 'Sin: 1 ingrediente(s)'.
        """
        producto_ids: set[int] = {
            d.producto_id
            for p in pedidos
            for d in p.detalles
            if d.personalizacion
        }
        if not producto_ids:
            return

        nombre_map: dict[int, dict[int, str]] = {}
        for pid in producto_ids:
            producto = ProductoRepository(self._session).get_by_id(pid)
            if not producto:
                continue
            nombre_map[pid] = {
                enlace.ingrediente_id: getattr(enlace.ingrediente, 'nombre', str(enlace.ingrediente_id))
                for enlace in producto.ingredientes_enlaces
            }

        for p in pedidos:
            for d in p.detalles:
                if d.personalizacion:
                    nombres = nombre_map.get(d.producto_id, {})
                    d.personalizacion_nombres = [
                        nombres[i] for i in d.personalizacion if i in nombres
                    ] or None

    def _enriquecer_personalizaciones_admin(
        self, detalles: List[DetallePedidoPublic]
    ) -> None:
        """
        Versión del helper de enriquecimiento para DetallePedidoPublic (PedidoAdmin).
        Resuelve IDs de ingredientes removidos a nombres legibles.
        Modifica in-place personalizacion_nombres de cada detalle.
        """
        producto_ids: set[int] = {
            d.producto_id for d in detalles if d.personalizacion
        }
        if not producto_ids:
            return

        nombre_map: dict[int, dict[int, str]] = {}
        for pid in producto_ids:
            producto = ProductoRepository(self._session).get_by_id(pid)
            if not producto:
                continue
            nombre_map[pid] = {
                enlace.ingrediente_id: getattr(enlace.ingrediente, 'nombre', str(enlace.ingrediente_id))
                for enlace in producto.ingredientes_enlaces
            }

        for d in detalles:
            if d.personalizacion:
                nombres = nombre_map.get(d.producto_id, {})
                d.personalizacion_nombres = [
                    nombres[i] for i in d.personalizacion if i in nombres
                ] or None

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
            raise ForbiddenError("No tienes permiso para acceder a este pedido.")

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
            usuario = UsuarioRepository(self._session).get_by_id(pedido.usuario_id)
            if usuario:
                usuario_nombre = getattr(usuario, 'nombre', None) or usuario_nombre
                usuario_email  = getattr(usuario, 'email',  '') or ''

            if pedido.direccion_id:
                dir_orm = DireccionRepository(self._session).get_sin_restriccion(pedido.direccion_id)
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

        # Enriquecer personalizaciones en los detalles del PedidoAdmin
        if detalles:
            self._enriquecer_personalizaciones_admin(detalles)

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
            tipo_entrega=pedido.tipo_entrega,
            tipo_entrega_label=_TIPO_ENTREGA_LABELS.get(
                pedido.tipo_entrega, pedido.tipo_entrega
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
