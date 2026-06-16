from datetime import datetime, timezone
from typing import Dict, List, NamedTuple, Optional

from fastapi import HTTPException, status
from sqlmodel import Session, select

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
from app.modules.catalogo.producto.models import Producto
from app.modules.catalogo.ingrediente.models import Ingrediente
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
    def crear_pedido(self, usuario_id: int, datos: PedidoCreate) -> PedidoCambioResult:
        # ── Validar stock ANTES de iniciar la transacción ──────────────────
        # Se construye una preview del pedido sin persistir nada.
        # Si falta stock, se lanza un error 400 antes de entrar al UoW.
        # El mensaje de detalle va en el response para debugging/admin;
        # el frontend del cliente muestra un mensaje genérico al usuario.
        faltantes_stock = self._obtener_resumen_stock_preview(datos)
        if faltantes_stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "stock_insuficiente",
                    "faltantes": faltantes_stock,
                },
            )

        with PedidoUnitOfWork(self._session) as uow:
            # 1. Validar productos y construir snapshots (precio + nombre congelados)
            detalles: List[DetallePedido] = []
            subtotal = 0.0
            # Mapa temporal producto_id → nombres de ingredientes removidos.
            # Se usa para enriquecer la respuesta Pydantic (no se persiste en la DB).
            nombres_por_producto: Dict[int, List[str]] = {}

            for item in datos.detalles:
                producto = self._session.get(Producto, item.producto_id)
                if not producto or not producto.activo:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Producto {item.producto_id} no disponible.",
                    )

                # Validar personalizaciones (ingredientes removidos)
                if item.personalizacion:
                    ingredientes_producto = {
                        e.ingrediente_id: e for e in producto.ingredientes_enlaces
                    }
                    for ing_id in item.personalizacion:
                        enlace = ingredientes_producto.get(ing_id)
                        if enlace is None:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"El ingrediente {ing_id} no pertenece al producto.",
                            )
                        if not enlace.es_removible:
                            nombre = getattr(enlace.ingrediente, "nombre", str(ing_id))
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"El ingrediente '{nombre}' no es removible.",
                            )

                precio = float(producto.precio)
                sub = round(precio * item.cantidad, 2)
                subtotal += sub

                # Construir lista de nombres de ingredientes removidos
                nombres_removidos = None
                if item.personalizacion:
                    nombres_removidos = [
                        ingredientes_producto[pid].ingrediente.nombre
                        for pid in item.personalizacion
                        if pid in ingredientes_producto
                    ]

                # Guardar nombres removidos en el mapa temporal para uso en la respuesta
                if nombres_removidos:
                    nombres_por_producto[item.producto_id] = nombres_removidos

                detalle = DetallePedido(
                    producto_id=item.producto_id,
                    cantidad=item.cantidad,
                    nombre_snapshot=producto.nombre,
                    precio_snapshot=precio,
                    subtotal_snap=sub,
                    personalizacion=item.personalizacion,
                )
                detalles.append(detalle)

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

            return PedidoCambioResult(
                pedido=response,
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

            # Descontar stock al confirmar el pedido y detectar alerta
            stock_bajo: Optional[List[dict]] = None
            if estado_nuevo == EstadoPedido.CONFIRMADO.value:
                cambios = self._descontar_stock(pedido)
                stock_bajo = self._detectar_stock_bajo_actual(cambios)

            # Devolver stock si se cancela desde un estado donde ya se había descontado
            # (el stock se descuenta al confirmar, por eso excluimos PENDIENTE)
            if estado_nuevo == EstadoPedido.CANCELADO.value and estado_actual != EstadoPedido.PENDIENTE.value:
                self._devolver_stock(pedido)

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
            return PedidoCambioResult(
                pedido=response,
                historial=HistorialEstadoPublic.model_validate(historial),
                stock_bajo=stock_bajo,
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

            # Devolver stock si el pedido ya estaba confirmado
            # (stock solo se descuenta al pasar a CONFIRMADO)
            if estado_actual != EstadoPedido.PENDIENTE.value:
                self._devolver_stock(pedido)

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
            return PedidoCambioResult(
                pedido=response,
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
            producto = self._session.get(Producto, pid)
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
            producto = self._session.get(Producto, pid)
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

    # ====================================================================
    # STOCK — DESCUENTO Y DEVOLUCIÓN DE INGREDIENTES/PRODUCTOS
    # ====================================================================

    def _descontar_stock(self, pedido: Pedido) -> List[dict]:
        """
        Descuenta stock de ingredientes al confirmar un pedido.
        Se llama cuando el pedido pasa a CONFIRMADO.

        El stock de los productos se deriva de sus ingredientes; no se maneja
        producto.stock_cantidad de forma independiente.

        Lógica:
        - Por cada ingrediente requerido (no removido): ingrediente.stock -= cantidad_requerida * cantidad

        Validación:
        - ANTES de descontar, verifica que haya stock suficiente de ingredientes.
        - Si algún ingrediente no tiene stock, lanza HTTPException(409)
          y NO aplica ningún descuento (el pedido queda en PENDIENTE).

        Returns:
            Lista de dicts con {tipo, id, nombre, stock_anterior, stock_nuevo}
            para construir el mensaje de notificación.
        """
        # ── Pre-validación: verificar stock suficiente antes de descontar ──
        faltantes: List[dict] = []

        for detalle in pedido.detalles:
            producto = self._session.get(Producto, detalle.producto_id)
            if not producto:
                continue

            # Validar stock de ingredientes (el stock del producto se deriva de sus ingredientes;
            # no se valida producto.stock_cantidad de forma independiente)
            # TODO: eliminar campo producto.stock_cantidad en futuras migraciones.
            removidos = set(detalle.personalizacion or [])
            for enlace in producto.ingredientes_enlaces:
                if enlace.ingrediente_id in removidos:
                    continue
                ingrediente = self._session.get(Ingrediente, enlace.ingrediente_id)
                if not ingrediente:
                    continue
                cantidad_requerida = float(enlace.cantidad_requerida) * detalle.cantidad
                if ingrediente.stock < cantidad_requerida:
                    faltantes.append({
                        "tipo": "INGREDIENTE",
                        "id": ingrediente.id,
                        "nombre": ingrediente.nombre,
                        "requerido": cantidad_requerida,
                        "disponible": ingrediente.stock,
                    })

        if faltantes:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "stock_insuficiente_al_confirmar",
                    "pedido_id": pedido.id,
                    "faltantes": faltantes,
                },
            )

        # ── Descuento real ──
        cambios: List[dict] = []

        for detalle in pedido.detalles:
            producto = self._session.get(Producto, detalle.producto_id)
            if not producto:
                continue

            # Obtener mapa de ingredientes removidos para este detalle
            removidos = set(detalle.personalizacion or [])

            # Descontar ingredientes requeridos (excepto los removidos por el cliente)
            for enlace in producto.ingredientes_enlaces:
                if enlace.ingrediente_id in removidos:
                    # El cliente removió este ingrediente, no se consume
                    continue

                ingrediente = self._session.get(Ingrediente, enlace.ingrediente_id)
                if not ingrediente:
                    continue

                cantidad_a_restar = float(enlace.cantidad_requerida) * detalle.cantidad
                stock_anterior_ing = float(ingrediente.stock)
                ingrediente.stock = max(0.0, float(ingrediente.stock) - cantidad_a_restar)
                self._session.add(ingrediente)
                cambios.append({
                    "tipo": "INGREDIENTE",
                    "id": ingrediente.id,
                    "nombre": ingrediente.nombre,
                    "stock_anterior": stock_anterior_ing,
                    "stock_nuevo": float(ingrediente.stock),
                })

        return cambios

    def _devolver_stock(self, pedido: Pedido) -> List[dict]:
        """
        Devuelve stock de ingredientes al cancelar un pedido confirmado.
        Se llama cuando se cancela un pedido que ya estaba CONFIRMADO, EN_PREPARACION
        o EN_CAMINO (el stock ya fue descontado).

        El stock de los productos se deriva de sus ingredientes; no se maneja
        producto.stock_cantidad de forma independiente.

        Lógica:
        - ingrediente.stock += cantidad_requerida * cantidad
        """
        cambios: List[dict] = []

        for detalle in pedido.detalles:
            producto = self._session.get(Producto, detalle.producto_id)
            if not producto:
                continue

            # Obtener mapa de ingredientes removidos para este detalle
            removidos = set(detalle.personalizacion or [])

            # Devolver ingredientes requeridos (excepto los removidos por el cliente)
            for enlace in producto.ingredientes_enlaces:
                if enlace.ingrediente_id in removidos:
                    continue

                ingrediente = self._session.get(Ingrediente, enlace.ingrediente_id)
                if not ingrediente:
                    continue

                cantidad_a_devolver = float(enlace.cantidad_requerida) * detalle.cantidad
                stock_anterior_ing = float(ingrediente.stock)
                ingrediente.stock = float(ingrediente.stock) + cantidad_a_devolver
                self._session.add(ingrediente)
                cambios.append({
                    "tipo": "INGREDIENTE",
                    "id": ingrediente.id,
                    "nombre": ingrediente.nombre,
                    "stock_anterior": stock_anterior_ing,
                    "stock_nuevo": float(ingrediente.stock),
                })

        return cambios

    # ====================================================================
    # VALIDACIÓN DE STOCK EN CREAR_PEDIDO
    # ====================================================================

    def _obtener_resumen_stock_preview(self, datos: PedidoCreate) -> List[dict]:
        """
        Valida disponibilidad de stock ANTES de crear el pedido.
        Recibe el schema de request (PedidoCreate) — sin aún tener un pedido ORM.
        Retorna lista de faltantes (vacía si todo OK).
        """
        resumen: List[dict] = []

        for item in datos.detalles:
            producto = self._session.get(Producto, item.producto_id)
            if not producto:
                # El error de "producto no existe" se maneja más arriba en crear_pedido
                continue

            removidos = set(item.personalizacion or [])

            # Ingredientes (el stock del producto se deriva de sus ingredientes;
            # no se valida producto.stock_cantidad de forma independiente)
            # TODO: eliminar campo producto.stock_cantidad en futuras migraciones.
            for enlace in producto.ingredientes_enlaces:
                if enlace.ingrediente_id in removidos:
                    continue
                ingrediente = self._session.get(Ingrediente, enlace.ingrediente_id)
                if not ingrediente:
                    continue
                requerido = float(enlace.cantidad_requerida) * item.cantidad
                disponible = float(ingrediente.stock)
                if disponible < requerido:
                    resumen.append({
                        "tipo": "INGREDIENTE",
                        "id": ingrediente.id,
                        "nombre": ingrediente.nombre,
                        "requerido": requerido,
                        "disponible": disponible,
                        "ok": False,
                    })

        return resumen

    # ====================================================================
    # DETECCIÓN DE STOCK BAJO TRAS DESCONTAR (avanzar_estado → CONFIRMADO)
    # ====================================================================

    def _detectar_stock_bajo_actual(self, cambios_stock: List[dict]) -> List[dict]:
        """
        Recibe la lista de cambios devuelta por _descontar_stock y consulta
        el stock actual de los ingredientes afectados.
        Retorna la lista de ingredientes cuyo stock quedó por debajo de su
        umbral de seguridad, con todos los datos necesarios para el payload
        del WebSocket.

        Returns:
            Lista de dicts con {id, nombre, stock_actual, stock_seguridad, unidad}
        """
        criticos: List[dict] = []

        for cambio in cambios_stock:
            if cambio["tipo"] != "INGREDIENTE":
                continue

            ingrediente = self._session.get(Ingrediente, cambio["id"])
            if not ingrediente:
                continue

            seguridad = getattr(ingrediente, "stock_seguridad", None)
            if seguridad is None:
                continue

            if float(ingrediente.stock) < float(seguridad):
                criticos.append({
                    "id": ingrediente.id,
                    "nombre": ingrediente.nombre,
                    "stock_actual": float(ingrediente.stock),
                    "stock_seguridad": float(seguridad),
                    "unidad": getattr(ingrediente, "unidad", "u"),
                })

        return criticos

    # ====================================================================
    # PREVIEW DE STOCK (para _obtener_resumen_stock — existente)
    # ====================================================================

    def _obtener_resumen_stock(self, pedido: Pedido) -> List[dict]:
        """
        Retorna una预览 del impacto en stock sin modificar nada.
        Útil para validar disponibilidad antes de confirmar.
        """
        resumen: List[dict] = []

        for detalle in pedido.detalles:
            producto = self._session.get(Producto, detalle.producto_id)
            if not producto:
                continue

            removidos = set(detalle.personalizacion or [])

            # Producto
            if producto.stock_cantidad < detalle.cantidad:
                resumen.append({
                    "tipo": "PRODUCTO",
                    "id": producto.id,
                    "nombre": producto.nombre,
                    "requerido": detalle.cantidad,
                    "disponible": producto.stock_cantidad,
                    "ok": False,
                })

            # Ingredientes
            for enlace in producto.ingredientes_enlaces:
                if enlace.ingrediente_id in removidos:
                    continue

                ingrediente = self._session.get(Ingrediente, enlace.ingrediente_id)
                if not ingrediente:
                    continue

                requerido = float(enlace.cantidad_requerida) * detalle.cantidad
                disponible = float(ingrediente.stock)
                if disponible < requerido:
                    resumen.append({
                        "tipo": "INGREDIENTE",
                        "id": ingrediente.id,
                        "nombre": ingrediente.nombre,
                        "requerido": requerido,
                        "disponible": disponible,
                        "ok": False,
                    })

        return resumen
