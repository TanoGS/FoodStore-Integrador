import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { PedidoService, type Pedido } from '../../services/pedido.service';
import { PagosService } from '../../services/pagos.service';
import { usePedidoEventos } from '../../hooks/usePedidoWebSocket';
import type { WSEvent } from '../../store/wsStore';
import {
  Banknote, Clock, AlertTriangle, Timer,
  Loader2, User, ChefHat, Truck, Package,
  CheckCircle2, X, Check, XCircle, RefreshCw,
} from 'lucide-react';
import MotivoModal from './MotivoModal';

type DetallePedido = Pedido['detalles'][number];

// Todos los estados que ve el cajero (incluye PENDIENTE para EFECTIVO)
const CAJERO_ESTADOS = [
  'PENDIENTE',
  'CONFIRMADO',
  'EN_PREPARACION',
  'EN_CAMINO',
  'ENTREGADO',
  'CANCELADO',
] as const;
type CajeroEstado = typeof CAJERO_ESTADOS[number];

// Filtros (excluye PENDIENTE de las tabs normales)
type FiltroKey = 'todos' | 'en_curso' | 'listos' | 'entregados';
const FILTROS: { key: FiltroKey; label: string; match: (e: string) => boolean }[] = [
  { key: 'todos',      label: 'Todos',              match: () => true },
  { key: 'en_curso',   label: 'En Cocina',          match: (e) => e === 'CONFIRMADO' || e === 'EN_PREPARACION' },
  { key: 'listos',     label: 'Listos p/ Entregar', match: (e) => e === 'EN_CAMINO' },
  { key: 'entregados', label: 'Entregados',         match: (e) => e === 'ENTREGADO' },
];

const TIPO_ENTREGA_BADGE: Record<string, { label: string; cls: string }> = {
  EN_LOCAL: { label: 'LOCAL', cls: 'bg-orange-700 text-orange-100' },
  DELIVERY: { label: 'DELIV', cls: 'bg-blue-700   text-blue-100'  },
};

const CAJERO_BADGE: Record<string, { label: string; cls: string }> = {
  PENDIENTE:       { label: 'Pago Efectivo', cls: 'bg-yellow-500 text-white' },
  CONFIRMADO:      { label: 'En Cocina',    cls: 'bg-blue-500   text-white' },
  EN_PREPARACION:  { label: 'Preparando',    cls: 'bg-orange-500 text-white' },
  EN_CAMINO:       { label: 'Listo',        cls: 'bg-purple-500 text-white' },
  ENTREGADO:       { label: 'Entregado',    cls: 'bg-green-500  text-white' },
  CANCELADO:       { label: 'Cancelado',    cls: 'bg-red-500    text-white' },
};

const TINTE_FILA: Record<string, string> = {
  PENDIENTE:       'bg-yellow-900/20 hover:bg-yellow-900/35',
  CONFIRMADO:      'bg-blue-900/15  hover:bg-blue-900/25',
  EN_PREPARACION:  'bg-orange-900/15 hover:bg-orange-900/25',
  EN_CAMINO:       'bg-purple-900/15 hover:bg-purple-900/25',
  ENTREGADO:       'bg-green-900/10 hover:bg-green-900/20',
  CANCELADO:       'bg-red-900/10   hover:bg-red-900/20',
};

function resumenProductos(detalles: DetallePedido[]): string {
  return detalles.map((d) => `${d.cantidad}× ${d.nombre_snapshot}`).join(', ');
}

function minutosEnEstado(pedido: Pedido): number {
  const desde = pedido.actualizado_en ?? pedido.creado_en;
  return Math.floor((Date.now() - new Date(desde).getTime()) / 60_000);
}

function etiquetaTimer(estado: string): string {
  switch (estado) {
    case 'PENDIENTE':      return 'esperando';
    case 'CONFIRMADO':     return 'esperando';
    case 'EN_PREPARACION': return 'preparando';
    case 'EN_CAMINO':      return 'listo';
    case 'ENTREGADO':      return 'entregado';
    default:               return 'hace';
  }
}

function timerColor(min: number): string {
  if (min < 5)  return 'text-green-400';
  if (min < 15) return 'text-yellow-400';
  return 'text-red-400';
}

// ─────────────────────────────────────────────────────────────────────
export default function VistaCajero() {
  const { user, isAuthenticated } = useAuthStore();
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ tipo: 'ok'|'err'; msg: string } | null>(null);
  const [filtroActivo, setFiltroActivo] = useState<FiltroKey>('todos');
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [modalMotivo, setModalMotivo] = useState<{ pedidoId: number } | null>(null);
  const [procesando, setProcesando] = useState<Set<number>>(new Set());
  const [sincronizando, setSincronizando] = useState<Set<number>>(new Set());
  /**
   * Cache local del mp_status de cada pedido que fue verificado.
   * Se actualiza después de cada sincronización para que el frontend
   * se entere del resultado sin depender de que el pedido avance de estado.
   * Si el pedido avanza a CONFIRMADO, sale de la lista de pendientes
   * automáticamente y desaparece de aquí.
   */
  const [localPagoStatus, setLocalPagoStatus] = useState<Record<number, string>>({});

  const isCajero = useMemo(
    () => user?.roles?.some((r) => r.codigo === 'CAJERO' || r.codigo === 'ADMIN') ?? false,
    [user?.roles]
  );

  if (!isAuthenticated || !isCajero) {
    return <Navigate to="/admin" replace />;
  }

  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 60_000);
    return () => clearInterval(id);
  }, []);

  const cargarPedidos = useCallback(async () => {
    try {
      const todos = await PedidoService.listarTodos();
      setPedidos(todos.filter((p) => CAJERO_ESTADOS.includes(p.estado_codigo as CajeroEstado)));
    } catch {
      setToast({ tipo: 'err', msg: 'Error al cargar pedidos' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { cargarPedidos(); }, [cargarPedidos]);

  useEffect(() => {
    if (!toast) return;
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 4000);
    return () => { if (toastTimer.current) clearTimeout(toastTimer.current); };
  }, [toast]);

  // ── WebSocket ─────────────────────────────────────────────────────
  const handleEvent = useCallback((ev: WSEvent) => {
    if (ev.type === 'pedido.creado') {
      const payload = ev.payload as { pedido: { id: number; estado_codigo: string } };
      if (CAJERO_ESTADOS.includes(payload.pedido.estado_codigo as CajeroEstado)) {
        setToast({ tipo: 'ok', msg: '🔔 Nuevo pedido recibido' });
        cargarPedidos();
      }
    } else if (ev.type === 'pedido.estado.cambiado') {
      const payload = ev.payload as { estado_hacia: string; pedido: { id: number } };
      if (CAJERO_ESTADOS.includes(payload.estado_hacia as CajeroEstado)) {
        cargarPedidos();
      } else {
        setPedidos((prev) => prev.filter((p) => p.id !== payload.pedido.id));
      }
    }
  }, [cargarPedidos]);

  usePedidoEventos(handleEvent);

  // ── Acciones del cajero ─────────────────────────────────────────
  const confirmarEfectivo = useCallback(async (pedidoId: number) => {
    setProcesando(prev => new Set(prev).add(pedidoId));
    try {
      await PedidoService.actualizarEstado(pedidoId, 'CONFIRMADO');
      setToast({ tipo: 'ok', msg: `Pedido #${pedidoId} confirmado. Se envía a cocina.` });
    } catch {
      setToast({ tipo: 'err', msg: `Error al confirmar pedido #${pedidoId}` });
    } finally {
      setProcesando(prev => { const s = new Set(prev); s.delete(pedidoId); return s; });
    }
  }, []);

  const cancelarPedido = useCallback(async (pedidoId: number, motivo: string) => {
    setProcesando(prev => new Set(prev).add(pedidoId));
    try {
      await PedidoService.actualizarEstado(pedidoId, 'CANCELADO', motivo);
      setToast({ tipo: 'ok', msg: `Pedido #${pedidoId} cancelado.` });
    } catch {
      setToast({ tipo: 'err', msg: `Error al cancelar pedido #${pedidoId}` });
    } finally {
      setProcesando(prev => { const s = new Set(prev); s.delete(pedidoId); return s; });
    }
  }, []);

  /** Consulta MercadoPago para verificar si el pago fue aprobado. */
  const verificarMP = useCallback(async (pedidoId: number) => {
    setSincronizando(prev => new Set(prev).add(pedidoId));
    try {
      const pago = await PagosService.sincronizar(pedidoId);
      if (pago.mp_status === 'approved') {
        setLocalPagoStatus(prev => ({ ...prev, [pedidoId]: 'approved' }));
        setToast({ tipo: 'ok', msg: `✅ Pago #${pedidoId} APROBADO en MercadoPago. El pedido avanza a cocina automáticamente.` });
      } else if (pago.mp_status === 'not_found') {
        setLocalPagoStatus(prev => ({ ...prev, [pedidoId]: 'not_found' }));
        setToast({ tipo: 'err', msg: `⚠️ Pedido #${pedidoId}: MercadoPago no tiene registro del pago. ¿El cliente cerró la página antes de pagar?` });
      } else {
        setLocalPagoStatus(prev => ({ ...prev, [pedidoId]: pago.mp_status }));
        setToast({ tipo: 'ok', msg: `⏳ Pedido #${pedidoId}: MercadoPago dice "${pago.mp_status}". El pago aún está pendiente. Reintentá en unos minutos.` });
      }
      // Refrescar la lista para que el pedido desaparezca de "Esperando MP"
      // si ya fue aprobado y avanzó a CONFIRMADO (DELIVERY).
      await cargarPedidos();
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? 'No se pudo conectar con MercadoPago. Verificá que el backend tenga MP_ACCESS_TOKEN configurado.';
      setToast({ tipo: 'err', msg: `❌ Error verificando pago #${pedidoId}: ${msg}` });
    } finally {
      setSincronizando(prev => { const s = new Set(prev); s.delete(pedidoId); return s; });
    }
  }, [cargarPedidos]);

  // ── Datos separados ──────────────────────────────────────────────
  // Solo MP que NO fue aprobado localmente (los approved se mueven a pendientesEfectivo).
  const pendientesMP = useMemo(
    () => pedidos.filter(
      (p) => p.estado_codigo === 'PENDIENTE'
        && p.forma_pago_codigo === 'MERCADOPAGO'
        && localPagoStatus[p.id] !== 'approved'
    ),
    [pedidos, localPagoStatus]
  );

  // Efectivo real + MP ya aprobado localmente (esperando confirmación del retiro/entrega).
  const pendientesEfectivo = useMemo(
    () => pedidos.filter(
      (p) => p.estado_codigo === 'PENDIENTE'
        && (
          p.forma_pago_codigo === 'EFECTIVO'
          || (p.forma_pago_codigo === 'MERCADOPAGO' && localPagoStatus[p.id] === 'approved')
        )
    ),
    [pedidos, localPagoStatus]
  );

  const pedidosCiclo = useMemo(() => {
    const filtro = FILTROS.find((f) => f.key === filtroActivo);
    return pedidos.filter(
      (p) => p.estado_codigo !== 'PENDIENTE' && (!filtro || filtro.match(p.estado_codigo))
    );
  }, [pedidos, filtroActivo]);

  const conteos = useMemo(() => ({
    todos:      pedidosCiclo.length,
    en_curso:   pedidosCiclo.filter((p) => p.estado_codigo === 'CONFIRMADO' || p.estado_codigo === 'EN_PREPARACION').length,
    listos:     pedidosCiclo.filter((p) => p.estado_codigo === 'EN_CAMINO').length,
    entregados: pedidosCiclo.filter((p) => p.estado_codigo === 'ENTREGADO').length,
  }), [pedidosCiclo]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <Loader2 className="w-12 h-12 text-yellow-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white p-6">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="bg-yellow-500 p-3 rounded-2xl">
            <Banknote className="w-8 h-8 text-slate-900" />
          </div>
          <div>
            <h1 className="text-3xl font-black tracking-tight">CAJERO</h1>
            <p className="text-yellow-400 text-sm font-medium">
              {pendientesEfectivo.length > 0 && (
                <span className="mr-3">{pendientesEfectivo.length} pendientes de pago</span>
              )}
              {conteos.en_curso} en cocina · {conteos.listos} listos · {conteos.entregados} entregados
            </p>
          </div>
        </div>
        <button onClick={cargarPedidos} className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded-xl text-sm font-bold transition-colors">
          <Clock className="w-4 h-4" /> Actualizar
        </button>
      </div>

      {/* ── Toast ─────────────────────────────────────────────────── */}
      {toast && (
        <div className={`mb-6 flex items-center gap-3 px-5 py-3 rounded-xl border-2 text-sm font-bold ${
          toast.tipo === 'ok' ? 'bg-green-900/60 border-green-500 text-green-300' : 'bg-red-900/60 border-red-500 text-red-300'
        }`}>
          {toast.tipo === 'ok' ? <CheckCircle2 className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
          {toast.msg}
        </div>
      )}

      {/* ── Pedidos pendientes de MercadoPago ───────────────────────── */}
      {pendientesMP.length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-black text-blue-400 mb-3 flex items-center gap-2">
            <RefreshCw className="w-5 h-5" />
            MercadoPago — Esperando confirmación de pago
          </h2>
          <div className="space-y-3">
            {pendientesMP.map((p) => (
              <div
                key={p.id}
                className="bg-blue-900/30 border border-blue-600/40 rounded-2xl p-5 flex items-center gap-4 flex-wrap"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-2xl font-black text-white">#{p.id}</span>
                    <span className="bg-blue-600 text-white text-[10px] font-black uppercase px-2 py-0.5 rounded-full">
                      MercadoPago
                    </span>
                    {(p as any).tipo_entrega && (
                      <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full ${
                        TIPO_ENTREGA_BADGE[(p as any).tipo_entrega]?.cls ?? 'bg-slate-600 text-white'
                      }`}>
                        {TIPO_ENTREGA_BADGE[(p as any).tipo_entrega]?.label ?? (p as any).tipo_entrega}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-sm text-blue-200/80">
                    <span className="flex items-center gap-1">
                      <User className="w-3.5 h-3.5" /> #{p.usuario_id}
                    </span>
                    <span className="max-w-xs truncate">{resumenProductos(p.detalles)}</span>
                  </div>
                  <p className="text-xs text-blue-300/60 mt-1">
                    Esperando que MercadoPago confirme el pago. Si pasaron más de 5 minutos y no cambió el estado,
                    hacé clic en "Verificar con MP".
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-2xl font-black text-blue-400">${p.total.toFixed(2)}</div>
                  <div className={`text-xs font-bold ${timerColor(minutosEnEstado(p))}`}>
                    {minutosEnEstado(p) < 1 ? 'recién' : `hace ${minutosEnEstado(p)}m`}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => verificarMP(p.id)}
                    disabled={sincronizando.has(p.id) || procesando.has(p.id)}
                    className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 text-white px-4 py-2 rounded-xl font-bold text-sm transition-colors"
                    title="Consulta MercadoPago para verificar si el pago fue aprobado"
                  >
                    {sincronizando.has(p.id) ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <RefreshCw className="w-4 h-4" />
                    )}
                    Verificar con MP
                  </button>
                  <button
                    onClick={() => setModalMotivo({ pedidoId: p.id })}
                    disabled={sincronizando.has(p.id) || procesando.has(p.id)}
                    className="flex items-center gap-1.5 bg-red-600 hover:bg-red-500 disabled:bg-slate-700 text-white px-4 py-2 rounded-xl font-bold text-sm transition-colors"
                    title="Cancelar pedido — el pago no fue acreditado"
                  >
                    <X className="w-4 h-4" />
                    Cancelar
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Pedidos pendientes de pago en efectivo ─────────────────── */}
      {pendientesEfectivo.length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-black text-yellow-400 mb-3 flex items-center gap-2">
            <Banknote className="w-5 h-5" />
            Pendientes de Pago en Efectivo
          </h2>
          <div className="space-y-3">
            {pendientesEfectivo.map((p) => (
              <div
                key={p.id}
                className="bg-yellow-900/30 border border-yellow-600/40 rounded-2xl p-5 flex items-center gap-4 flex-wrap"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-2xl font-black text-white">#{p.id}</span>
                    {p.forma_pago_codigo === 'MERCADOPAGO' && localPagoStatus[p.id] === 'approved' ? (
                      <span className="bg-green-500 text-white text-[10px] font-black uppercase px-2 py-0.5 rounded-full">
                        Pagado con MP
                      </span>
                    ) : (
                      <span className="bg-yellow-500 text-white text-[10px] font-black uppercase px-2 py-0.5 rounded-full">
                        Pago en efectivo
                      </span>
                    )}
                    {(p as any).tipo_entrega && (
                      <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full ${
                        TIPO_ENTREGA_BADGE[(p as any).tipo_entrega]?.cls ?? 'bg-slate-600 text-white'
                      }`}>
                        {TIPO_ENTREGA_BADGE[(p as any).tipo_entrega]?.label ?? (p as any).tipo_entrega}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-sm text-yellow-200/80">
                    <span className="flex items-center gap-1">
                      <User className="w-3.5 h-3.5" /> #{p.usuario_id}
                    </span>
                    <span className="max-w-xs truncate">{resumenProductos(p.detalles)}</span>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-2xl font-black text-yellow-400">${p.total.toFixed(2)}</div>
                  <div className={`text-xs font-bold ${timerColor(minutosEnEstado(p))}`}>
                    {minutosEnEstado(p) < 1 ? 'recién' : `hace ${minutosEnEstado(p)}m`}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => confirmarEfectivo(p.id)}
                    disabled={procesando.has(p.id)}
                    className="flex items-center gap-1.5 bg-green-600 hover:bg-green-500 disabled:bg-slate-700 text-white px-4 py-2 rounded-xl font-bold text-sm transition-colors"
                  >
                    {procesando.has(p.id) ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Check className="w-4 h-4" />
                    )}
                    Confirmar
                  </button>
                  <button
                    onClick={() => setModalMotivo({ pedidoId: p.id })}
                    disabled={procesando.has(p.id)}
                    className="flex items-center gap-1.5 bg-red-600 hover:bg-red-500 disabled:bg-slate-700 text-white px-4 py-2 rounded-xl font-bold text-sm transition-colors"
                  >
                    <X className="w-4 h-4" />
                    Cancelar
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Tabs de filtro ─────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2 mb-4 border-b border-slate-800 pb-1">
        {FILTROS.map((f) => {
          const count = conteos[f.key];
          const active = filtroActivo === f.key;
          return (
            <button
              key={f.key}
              onClick={() => setFiltroActivo(f.key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-t-lg text-sm font-bold transition-colors ${
                active ? 'bg-slate-800 text-white border-b-2 border-yellow-500' : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
              }`}
            >
              <span>{f.label}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-black ${
                active ? 'bg-yellow-500 text-slate-900' : 'bg-slate-700 text-slate-300'
              }`}>{count}</span>
            </button>
          );
        })}
      </div>

      {/* ── Tabla ─────────────────────────────────────────────────── */}
      {pedidosCiclo.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-slate-500">
          <Banknote className="w-20 h-20 mb-4 opacity-30" />
          <p className="text-2xl font-bold">
            No hay pedidos{filtroActivo !== 'todos' ? ` en "${FILTROS.find(f => f.key === filtroActivo)?.label}"` : ''}
          </p>
          <p className="text-sm mt-2">Los pedidos aparecerán aquí automáticamente.</p>
        </div>
      ) : (
        <div className="bg-slate-800/30 border border-slate-700 rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-900/80 text-xs uppercase text-slate-400 tracking-wider">
                <tr>
                  <th className="px-4 py-3 text-left font-bold">ID</th>
                  <th className="px-4 py-3 text-left font-bold">Cliente</th>
                  <th className="px-4 py-3 text-left font-bold">Estado</th>
                  <th className="px-4 py-3 text-left font-bold hidden md:table-cell">Pago</th>
                  <th className="px-4 py-3 text-left font-bold hidden lg:table-cell">Entrega</th>
                  <th className="px-4 py-3 text-left font-bold">Productos</th>
                  <th className="px-4 py-3 text-left font-bold">Tiempo</th>
                  <th className="px-4 py-3 text-right font-bold">Total</th>
                  <th className="px-4 py-3 text-right font-bold">Acción</th>
                </tr>
              </thead>
              <tbody>
                {pedidosCiclo.map((p) => (
                  <CajeroRow key={p.id} pedido={p} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Modal de motivo para cancelar ──────────────────────────── */}
      {modalMotivo && (
        <MotivoModal
          open={true}
          onConfirm={async (motivo) => {
            await cancelarPedido(modalMotivo.pedidoId, motivo);
            setModalMotivo(null);
          }}
          onClose={() => setModalMotivo(null)}
        />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Fila de la tabla (solo pedidos en ciclo operativo, sin PENDIENTE)
// ─────────────────────────────────────────────────────────────────────
function CajeroRow({ pedido }: { pedido: Pedido }) {
  const badge = CAJERO_BADGE[pedido.estado_codigo] ?? { label: pedido.estado_codigo, cls: 'bg-slate-600' };
  const tinteFila = TINTE_FILA[pedido.estado_codigo] ?? 'hover:bg-slate-800/50';
  const min = minutosEnEstado(pedido);

  const EstadoIcon =
    pedido.estado_codigo === 'EN_PREPARACION' ? ChefHat :
    pedido.estado_codigo === 'EN_CAMINO'      ? Truck    :
    pedido.estado_codigo === 'ENTREGADO'       ? Package  :
    null;

  return (
    <tr className={`border-b border-slate-800/50 transition-colors ${tinteFila}`}>
      <td className="px-4 py-3"><span className="text-lg font-black text-white">#{pedido.id}</span></td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1.5 text-slate-300">
          <User className="w-3.5 h-3.5 text-slate-500" />
          <span className="font-medium">#{pedido.usuario_id}</span>
        </div>
      </td>
      <td className="px-4 py-3">
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-black uppercase ${badge.cls}`}>
          {EstadoIcon && <EstadoIcon className="w-3 h-3" />}
          {badge.label}
        </span>
      </td>
      <td className="px-4 py-3 text-slate-300 text-xs hidden md:table-cell">{pedido.forma_pago_codigo}</td>
      <td className="px-4 py-3 hidden lg:table-cell">
        {(pedido as any).tipo_entrega ? (
          <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full ${
            TIPO_ENTREGA_BADGE[(pedido as any).tipo_entrega]?.cls ?? 'bg-slate-600 text-white'
          }`}>
            {TIPO_ENTREGA_BADGE[(pedido as any).tipo_entrega]?.label ?? (pedido as any).tipo_entrega}
          </span>
        ) : (
          <span className="text-[10px] text-slate-500">—</span>
        )}
      </td>
      <td className="px-4 py-3">
        <div className="max-w-xs truncate text-slate-200" title={resumenProductos(pedido.detalles)}>
          {resumenProductos(pedido.detalles)}
        </div>
      </td>
      <td className="px-4 py-3 whitespace-nowrap">
        <div className={`flex items-center gap-1.5 text-xs font-bold ${timerColor(min)}`}>
          <Timer className="w-3.5 h-3.5" />
          <span>{etiquetaTimer(pedido.estado_codigo)} {min < 1 ? 'recién' : `hace ${min}m`}</span>
        </div>
      </td>
      <td className="px-4 py-3 text-right">
        <span className="text-yellow-400 font-black">${pedido.total.toFixed(2)}</span>
      </td>
      <td className="px-4 py-3">
        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wide">—</span>
      </td>
    </tr>
  );
}
