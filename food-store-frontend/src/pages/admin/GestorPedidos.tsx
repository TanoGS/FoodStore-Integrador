import { useState, useCallback, useRef, type ElementType, Fragment } from 'react';
import { Navigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../../store/authStore';
import { EmptyState } from '../../components/common/EmptyState';
import { SkeletonAdminRow } from '../../components/common/SkeletonCard';
import {
  PedidoService,
  ESTADOS_FSM,
  ESTADOS_TERMINALES,
  ROLES_STAFF_PEDIDOS,
  type PedidoAdmin,
} from '../../services/pedido.service';
import { ConfiguracionService } from '../../services/configuracion.service';
import MotivoModal from './MotivoModal';
import { usePedidoEventos } from '../../hooks/usePedidoWebSocket';
import { useWSStore } from '../../store/wsStore';
import type { WSEvent, StockAlerta } from '../../store/wsStore';
import {
  ClipboardList,
  Clock,
  CheckCircle,
  ChefHat,
  Truck,
  Package,
  XCircle,
  AlertCircle,
  CheckCircle2,
  Loader2,
  ChevronDown,
  ChevronUp,
  MapPin,
  User,
  CreditCard,
  ShoppingBag,
  Pencil,
  Check,
} from 'lucide-react';

// ─── Config de la FSM ─────────────────────────────────────────────────

interface EstadoUIConfig {
  color: string;
  icon:  ElementType;
}

const ESTADOS_UI: Record<string, EstadoUIConfig> = {
  PENDIENTE:      { color: 'bg-yellow-900/60 text-yellow-300 border border-yellow-700/50', icon: Clock },
  CONFIRMADO:     { color: 'bg-blue-900/60 text-blue-300 border border-blue-700/50',    icon: CheckCircle },
  EN_PREPARACION: { color: 'bg-orange-900/60 text-orange-300 border border-orange-700/50', icon: ChefHat },
  EN_CAMINO:      { color: 'bg-purple-900/60 text-purple-300 border border-purple-700/50', icon: Truck },
  ENTREGADO:      { color: 'bg-green-900/60 text-green-300 border border-green-700/50',  icon: Package },
  CANCELADO:      { color: 'bg-red-900/60 text-red-300 border border-red-700/50',       icon: XCircle },
};

const ESTADOS_LABELS: Record<string, string> = {
  PENDIENTE:      'Pendiente',
  CONFIRMADO:     'Confirmado',
  EN_PREPARACION: 'En Preparación',
  EN_CAMINO:      'En Camino',
  ENTREGADO:      'Entregado',
  CANCELADO:      'Cancelado',
};

// Color del badge de forma de pago
const PAGO_CONFIG: Record<string, { color: string }> = {
  EFECTIVO:    { color: 'bg-emerald-900/60 text-emerald-300 border border-emerald-700/50' },
  MERCADOPAGO: { color: 'bg-amber-900/60 text-amber-300 border border-amber-700/50' },
};

// Badge de tipo de entrega
const TIPO_ENTREGA_BADGE: Record<string, { label: string; cls: string }> = {
  EN_LOCAL: { label: 'En el local', cls: 'bg-orange-900/60 text-orange-300 border border-orange-700/50' },
  DELIVERY: { label: 'Delivery',    cls: 'bg-blue-900/60 text-blue-300 border border-blue-700/50'  },
};

// ─── Tipos del modal de motivo ────────────────────────────────────────

type Feedback =
  | { tipo: 'ok';  msg: string }
  | { tipo: 'err'; msg: string }
  | null;

// ─── Componente principal ────────────────────────────────────────────

export default function GestorPedidos() {
  const { user, isAuthenticated } = useAuthStore();
  const queryClient = useQueryClient();
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [feedback,   setFeedback]   = useState<Feedback>(null);
  const [motivoCtx,   setMotivoCtx]  = useState<{ id: number; estado: string } | null>(null);

  const [periodo, setPeriodo] = useState<'TODOS' | 'DIARIO' | 'MENSUAL'>('TODOS');

  const [costoEnvio, setCostoEnvio] = useState<number | null>(null);
  const [editandoCosto, setEditandoCosto] = useState(false);
  const [costoEnvioInput, setCostoEnvioInput] = useState('');

  const [expandidas, setExpandidas] = useState<Set<number>>(new Set());
  const feedbackTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const canManageOrders = user?.roles?.some(
    (r) => ROLES_STAFF_PEDIDOS.includes(r.codigo)
  ) ?? false;

  // ─── useQuery: cargar pedidos ──────────────────────────────────────
  const { data: pedidos = [], isLoading: loading } = useQuery<PedidoAdmin[]>({
    queryKey: ['pedidos-admin', periodo],
    queryFn: () => PedidoService.listarTodosAdmin(periodo === 'TODOS' ? undefined : periodo),
    refetchInterval: false,
  });

  // ─── useMutation: cambio de estado ────────────────────────────────
  const cambiarEstadoMutation = useMutation({
    mutationFn: ({ id, nuevoEstado, motivo }: { id: number; nuevoEstado: string; motivo?: string }) =>
      PedidoService.actualizarEstado(id, nuevoEstado, motivo),
    onMutate: ({ id }) => setUpdatingId(id),
    onSuccess: (_data, { id, nuevoEstado }) => {
      queryClient.invalidateQueries({ queryKey: ['pedidos-admin'] });
      mostrarFeedback({
        tipo: 'ok',
        msg: `Pedido #${id} → "${ESTADOS_LABELS[nuevoEstado] ?? nuevoEstado}".`,
      });
    },
    onError: (error: unknown, { id }) => {
      const axiosErr = error as { response?: { status?: number; data?: { detail?: unknown } } };
      const status = axiosErr?.response?.status;
      const detail = axiosErr?.response?.data?.detail;
      const esStockInsuficiente =
        status === 409 &&
        typeof detail === 'object' &&
        (detail as { error?: string })?.error === 'stock_insuficiente_al_confirmar';

      let msg = 'No se pudo cambiar el estado. Verificá las reglas de transición.';
      if (esStockInsuficiente) {
        msg = `⚠️ El pedido #${id} no se puede confirmar: stock insuficiente.`;
      } else if (typeof detail === 'string') {
        msg = detail;
      }
      mostrarFeedback({ tipo: 'err', msg });
    },
    onSettled: () => setUpdatingId(null),
  });

  // ─── useMutation: guardar costo de envío ──────────────────────────
  const guardarCostoMutation = useMutation({
    mutationFn: (valor: number) => ConfiguracionService.setCostoEnvio(valor),
    onSuccess: (data: { costo_envio_delivery?: number }) => {
      setCostoEnvio(data?.costo_envio_delivery ?? null);
      setEditandoCosto(false);
    },
  });

  const handleGuardarCostoEnvio = () => {
    const valor = parseFloat(costoEnvioInput);
    if (isNaN(valor) || valor < 0) return;
    guardarCostoMutation.mutate(valor);
  };

  const ejecutarCambioEstado = (id: number, nuevoEstado: string, motivo?: string) => {
    cambiarEstadoMutation.mutate({ id, nuevoEstado, motivo });
  };

  const mostrarFeedback = (f: Feedback) => {
    if (feedbackTimer.current) clearTimeout(feedbackTimer.current);
    setFeedback(f);
    if (f) {
      feedbackTimer.current = setTimeout(() => setFeedback(null), 4000);
    }
  };

  // ─── WebSocket ────────────────────────────────────────────────────
  const handlePedidoEvent = useCallback((ev: WSEvent) => {
    if (ev.type === 'pedido.creado') {
      queryClient.invalidateQueries({ queryKey: ['pedidos-admin'] });
      const payload = ev.payload as { pedido: PedidoAdmin };
      mostrarFeedback({
        tipo: 'ok',
        msg: `Nuevo pedido #${payload.pedido.id} de ${payload.pedido.usuario_nombre} ($${payload.pedido.total.toFixed(2)}).`,
      });
    } else if (ev.type === 'pedido.estado.cambiado') {
      const payload = ev.payload as {
        pedido: PedidoAdmin;
        estado_hacia:     string;
        usuario_actor_id: number | null;
      };
      const myId = useAuthStore.getState().user?.id;
      if (payload.usuario_actor_id !== myId) {
        queryClient.invalidateQueries({ queryKey: ['pedidos-admin'] });
        mostrarFeedback({
          tipo: 'ok',
          msg: `Pedido #${payload.pedido.id} → ${ESTADOS_LABELS[payload.estado_hacia] ?? payload.estado_hacia}.`,
        });
      }
    } else if (ev.type === 'stock.alerta') {
      const alerta = ev.payload as StockAlerta;
      mostrarFeedback({
        tipo: 'err',
        msg: `⚠️ STOCK BAJO: "${alerta.ingrediente_nombre}" tiene ${alerta.stock_actual} ${alerta.unidad_medida}.`,
      });
    }
  }, [queryClient]);

  usePedidoEventos(handlePedidoEvent);

  const toggleExpand = (id: number) => {
    setExpandidas((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleCambiarEstado = (id: number, estadoActual: string, nuevoEstado: string) => {
    if (estadoActual === nuevoEstado) return;
    if (nuevoEstado === 'CANCELADO') {
      setMotivoCtx({ id, estado: estadoActual });
      return;
    }
    ejecutarCambioEstado(id, nuevoEstado);
  };

  const handleConfirmarMotivo = (motivo: string) => {
    if (!motivoCtx) return;
    const { id } = motivoCtx;
    setMotivoCtx(null);
    ejecutarCambioEstado(id, 'CANCELADO', motivo);
  };

  // ─── RBAC redirect ────────────────────────────────────────────────
  if (!isAuthenticated || !canManageOrders) {
    return <Navigate to="/" replace />;
  }

  // ─── Render ───────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-slate-900 text-white p-8">
      <div className="max-w-7xl mx-auto">

        {/* Header */}
        <div className="flex items-center gap-4 mb-6 border-b border-slate-700 pb-6">
          <div className="bg-slate-800 p-3 rounded-xl text-white">
            <ClipboardList className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-3xl font-black tracking-tight">
              Gestor de Pedidos
            </h1>
            <p className="text-slate-400">Panel operativo de ciclo de vida (FSM).</p>
          </div>
        </div>

        {/* ── Costo de envío configurable ────────────────────────────── */}
        <div className="mb-6 flex items-center gap-3 bg-slate-800/60 border border-slate-700 rounded-xl px-5 py-3">
          <Truck className="w-5 h-5 text-blue-400 shrink-0" />
          <span className="text-sm font-bold text-slate-300">Costo de envío DELIVERY:</span>
          {editandoCosto ? (
            <>
              <input
                type="number"
                min="0"
                step="0.01"
                value={costoEnvioInput}
                onChange={(e) => setCostoEnvioInput(e.target.value)}
                className="w-28 bg-slate-700 border border-slate-600 text-white text-sm rounded-lg px-3 py-1.5 outline-none focus:border-blue-500"
                autoFocus
                onKeyDown={(e) => { if (e.key === 'Enter') handleGuardarCostoEnvio(); if (e.key === 'Escape') setEditandoCosto(false); }}
              />
              <button
                onClick={handleGuardarCostoEnvio}
                disabled={guardarCostoMutation.isPending}
                className="flex items-center gap-1 bg-green-600 hover:bg-green-500 disabled:bg-slate-700 text-white px-3 py-1.5 rounded-lg text-sm font-bold transition-colors"
              >
                {guardarCostoMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                Guardar
              </button>
              <button
                onClick={() => { setEditandoCosto(false); setCostoEnvioInput(String(costoEnvio ?? '')); }}
                className="text-slate-400 hover:text-white text-sm px-2 py-1.5 rounded-lg transition-colors"
              >
                Cancelar
              </button>
            </>
          ) : (
            <>
              <span className="text-lg font-black text-blue-400">
                {costoEnvio !== null ? `$${costoEnvio.toFixed(2)}` : '...'}
              </span>
              <button
                onClick={() => { setEditandoCosto(true); setCostoEnvioInput(String(costoEnvio ?? 50)); }}
                className="flex items-center gap-1 text-slate-400 hover:text-white text-xs px-2 py-1 rounded-lg hover:bg-slate-700 transition-colors"
                title="Editar costo de envío"
              >
                <Pencil className="w-3.5 h-3.5" /> Editar
              </button>
            </>
          )}
          <span className="text-xs text-slate-500 ml-auto">Aplica a todos los pedidos nuevos</span>
        </div>

        {/* Feedback banner */}
        {feedback && (
          <div
            role="alert"
            className={`mb-6 flex items-start gap-3 p-4 rounded-xl border-2 ${
              feedback.tipo === 'ok'
                ? 'bg-green-900/60 border-green-500 text-green-300'
                : 'bg-red-900/60 border-red-500 text-red-300'
            }`}
          >
            {feedback.tipo === 'ok' ? (
              <CheckCircle2 className="w-5 h-5 mt-0.5 shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 mt-0.5 shrink-0" />
            )}
            <p className="font-bold text-sm flex-1">{feedback.msg}</p>
            <button
              type="button"
              onClick={() => mostrarFeedback(null)}
              className="text-current opacity-60 hover:opacity-100 transition-opacity"
              aria-label="Cerrar mensaje"
            >
              <XCircle className="w-5 h-5" />
            </button>
          </div>
        )}

        {/* Tabs de período */}
        <div className="flex gap-2 mb-6">
          {(['TODOS', 'DIARIO', 'MENSUAL'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriodo(p)}
              className={`px-4 py-2 rounded-lg font-bold text-sm transition-all ${
                periodo === p
                  ? 'bg-slate-800 text-white shadow-md'
                  : 'bg-slate-800/50 text-slate-400 border border-slate-700 hover:bg-slate-800'
              }`}
            >
              {p === 'TODOS' ? 'Todos' : p === 'DIARIO' ? 'Pedidos de Hoy' : 'Pedidos del Mes'}
            </button>
          ))}
        </div>

        {/* Tabla */}
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => <SkeletonAdminRow key={i} />)}
          </div>
        ) : pedidos.length === 0 ? (
          <EmptyState
            title="Sin pedidos"
            description="No hay pedidos en el período seleccionado."
          />
        ) : (
          <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-900/80 border-b border-slate-700 text-slate-400 text-xs uppercase tracking-wider">
                  <th className="p-3 font-bold">Pedido / Cliente</th>
                  <th className="p-3 font-bold">Fecha</th>
                  <th className="p-3 font-bold">Pago</th>
                  <th className="p-3 font-bold hidden xl:table-cell">Entrega</th>
                  <th className="p-3 font-bold">Dirección</th>
                  <th className="p-3 font-bold text-right">Total</th>
                  <th className="p-3 font-bold">Estado</th>
                  <th className="p-3 font-bold text-center">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {pedidos.map((pedido) => {
                  const UI      = ESTADOS_UI[pedido.estado_codigo] ?? ESTADOS_UI['PENDIENTE'];
                  const Icono   = UI.icon;
                  const estadoActual = pedido.estado_codigo;
                  const isTerminal   = ESTADOS_TERMINALES.includes(estadoActual);
                  const transiciones = ESTADOS_FSM[estadoActual] ?? [];
                  const isUpdating   = updatingId === pedido.id;
                  const expandida    = expandidas.has(pedido.id);
                  const pagoConfig   = PAGO_CONFIG[pedido.forma_pago_codigo] ?? { color: 'bg-slate-100 text-slate-700' };

                  return (
                    <Fragment key={pedido.id}>
                      {/* Fila principal */}
                      <tr
                        className="hover:bg-slate-700/30 transition-colors"
                      >
                        {/* Pedido / Cliente */}
                        <td className="p-3">
                          <p className="font-black text-white text-sm">
                            #{pedido.id}
                          </p>
                          <p className="text-slate-400 text-xs flex items-center gap-1 mt-0.5">
                            <User className="w-3 h-3" />
                            {pedido.usuario_nombre}
                          </p>
                          <p className="text-slate-500 text-[10px] truncate max-w-[160px]">
                            {pedido.usuario_email}
                          </p>
                        </td>

                        {/* Fecha */}
                        <td className="p-3 text-slate-400 text-xs">
                          {pedido.creado_en
                            ? new Date(pedido.creado_en).toLocaleString('es-AR', {
                                day: '2-digit',
                                month: '2-digit',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })
                            : '—'}
                        </td>

                        {/* Método de pago */}
                        <td className="p-3">
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold ${pagoConfig.color}`}
                          >
                        <CreditCard className="w-3 h-3" />
                            {pedido.forma_pago_label}
                          </span>
                        </td>

                        {/* Tipo de entrega */}
                        <td className="p-3 hidden xl:table-cell">
                          <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${
                            TIPO_ENTREGA_BADGE[pedido.tipo_entrega]?.cls ?? 'bg-slate-800 text-slate-300'
                          }`}>
                            {TIPO_ENTREGA_BADGE[pedido.tipo_entrega]?.label ?? pedido.tipo_entrega}
                          </span>
                        </td>

                        {/* Dirección */}
                        <td className="p-3">
                          {pedido.direccion ? (
                            <div className="flex items-start gap-1 text-slate-300 text-xs">
                              <MapPin className="w-3 h-3 mt-0.5 shrink-0 text-slate-500" />
                              <span className="leading-tight">
                                {[pedido.direccion.calle, pedido.direccion.numero]
                                  .filter(Boolean)
                                  .join(' ')}
                                {pedido.direccion.ciudad
                                  ? `, ${pedido.direccion.ciudad}`
                                  : ''}
                              </span>
                            </div>
                          ) : (
                            <span className="text-slate-500 text-xs">—</span>
                          )}
                        </td>

                        {/* Total */}
                        <td className="p-3 text-right">
                          <span className="font-black text-yellow-400 text-base">
                            ${pedido.total.toFixed(2)}
                          </span>
                        </td>

                        {/* Estado */}
                        <td className="p-3">
                          <span
                            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${UI.color}`}
                          >
                            <Icono className="w-4 h-4" />
                            {ESTADOS_LABELS[estadoActual] ?? estadoActual.replace('_', ' ')}
                          </span>
                        </td>

                        {/* Acciones: expandir productos + cambiar estado */}
                        <td className="p-3">
                          <div className="flex items-center justify-center gap-2 flex-wrap">
                            {/* Botón expand/collapse productos */}
                            <button
                              type="button"
                              onClick={() => toggleExpand(pedido.id)}
                              className={`p-1.5 rounded-lg border transition-colors ${
                                expandida
                                  ? 'bg-slate-700 text-white border-slate-600'
                                  : 'bg-slate-800 text-slate-300 border-slate-600 hover:bg-slate-700'
                              }`}
                              title={expandida ? 'Ocultar productos' : 'Ver productos'}
                              aria-label={`${expandida ? 'Ocultar' : 'Ver'} productos del pedido #${pedido.id}`}
                            >
                              {expandida ? (
                                <ChevronUp className="w-4 h-4" />
                              ) : (
                                <ChevronDown className="w-4 h-4" />
                              )}
                            </button>

                            {/* Spinner de loading */}
                            {isUpdating && (
                              <Loader2 className="w-4 h-4 text-slate-400 animate-spin" />
                            )}

                            {/* Select de transición FSM */}
                            <select
                              disabled={isTerminal || isUpdating}
                              className={`bg-slate-700 border border-slate-600 text-white text-xs rounded-lg p-1.5 outline-none disabled:opacity-50 disabled:cursor-not-allowed ${
                                isTerminal ? 'cursor-not-allowed' : ''
                              }`}
                              value={estadoActual}
                              onChange={(e) =>
                                handleCambiarEstado(pedido.id, estadoActual, e.target.value)
                              }
                              aria-label={`Cambiar estado del pedido #${pedido.id}`}
                            >
                              <option value={estadoActual}>
                                {ESTADOS_LABELS[estadoActual] ?? estadoActual} (actual)
                              </option>
                              {transiciones.length === 0 ? (
                                <option value={estadoActual} disabled>
                                  — Final —
                                </option>
                              ) : (
                                transiciones.map((est) => (
                                  <option key={est} value={est}>
                                    → {ESTADOS_LABELS[est] ?? est}
                                  </option>
                                ))
                              )}
                            </select>
                          </div>
                        </td>
                      </tr>

                      {/* Fila expandida: detalle de productos */}
                      {expandida && (
                        <tr key={`${pedido.id}-detalle`}>
                          <td colSpan={7} className="bg-slate-50 px-6 py-4 border-t border-slate-100">
                            <div className="bg-white rounded-xl border border-slate-200 p-4">
                              <div className="flex items-center gap-2 mb-3">
                                <ShoppingBag className="w-4 h-4 text-slate-500" />
                                <h4 className="font-bold text-slate-700 text-sm">
                                  Detalle del Pedido #{pedido.id}
                                </h4>
                              </div>
                              <div className="divide-y divide-slate-100">
                                {pedido.detalles.length === 0 ? (
                                  <p className="text-slate-400 text-sm py-2">Sin productos</p>
                                ) : (
                                  pedido.detalles.map((detalle, idx) => (
                                    <div
                                      key={idx}
                                      className="flex items-center justify-between py-2 text-sm"
                                    >
                                      <span className="text-slate-600">
                                        <span className="font-bold text-slate-800">
                                          {detalle.cantidad}×
                                        </span>{' '}
                                        {detalle.nombre_snapshot}
                                      </span>
                                      <span className="font-medium text-slate-700">
                                        ${detalle.subtotal_snap.toFixed(2)}
                                      </span>
                                    </div>
                                  ))
                                )}
                              </div>
                              {/* Totales desglosados */}
                              <div className="mt-3 pt-3 border-t border-slate-100 space-y-1">
                                <div className="flex justify-between text-xs text-slate-500">
                                  <span>Subtotal</span>
                                  <span>${pedido.subtotal.toFixed(2)}</span>
                                </div>
                                {pedido.descuento > 0 && (
                                  <div className="flex justify-between text-xs text-green-600">
                                    <span>Descuento</span>
                                    <span>-${pedido.descuento.toFixed(2)}</span>
                                  </div>
                                )}
                                <div className="flex justify-between text-xs text-slate-500">
                              <span>Envío</span>
                              <span>${pedido.costo_envio.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between text-xs text-slate-500">
                              <span>Tipo de entrega</span>
                              <span>{pedido.tipo_entrega_label}</span>
                            </div>
                                <div className="flex justify-between text-sm font-black text-slate-800 pt-1">
                                  <span>Total</span>
                                  <span>${pedido.total.toFixed(2)}</span>
                                </div>
                              </div>
                              {/* Notas del pedido */}
                              {pedido.notas && (
                                <div className="mt-3 pt-3 border-t border-slate-100">
                                  <p className="text-xs text-slate-500 font-medium">Notas:</p>
                                  <p className="text-sm text-slate-700 italic">"{pedido.notas}"</p>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}

                {pedidos.length === 0 && (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-slate-400">
                      No hay pedidos en el período seleccionado.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal de motivo de cancelación */}
      <MotivoModal
        open={motivoCtx !== null}
        onClose={() => setMotivoCtx(null)}
        onConfirm={handleConfirmarMotivo}
      />
    </div>
  );
}