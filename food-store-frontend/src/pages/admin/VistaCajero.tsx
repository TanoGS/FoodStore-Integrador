import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import {
  PedidoService,
  type Pedido,
} from '../../services/pedido.service';

// Tipo inferido del campo `detalles` del pedido (no requiere import extra)
type DetallePedido = Pedido['detalles'][number];
import { usePedidoEventos } from '../../hooks/usePedidoWebSocket';
import type { WSEvent } from '../../store/wsStore';
import {
  Banknote,
  Clock, AlertTriangle, Timer,
  Loader2, User, ChefHat, Truck, Package,
  CheckCircle2,
} from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────
// Tipos y config
// ─────────────────────────────────────────────────────────────────────
type CajeroPedido = Pedido;

// El cajero ya no recibe pedidos en PENDIENTE (nacen en CONFIRMADO
// desde el backend porque el pago se confirma online con MercadoPago).
// Por lo tanto solo ve los estados del ciclo operativo.
const CAJERO_ESTADOS = [
  'CONFIRMADO',
  'EN_PREPARACION',
  'EN_CAMINO',
  'ENTREGADO',
] as const;
type CajeroEstado = typeof CAJERO_ESTADOS[number];

// Filtros disponibles en la barra de tabs (sin "A Confirmar")
type FiltroKey = 'todos' | 'en_curso' | 'listos' | 'entregados';
const FILTROS: { key: FiltroKey; label: string; match: (e: string) => boolean }[] = [
  { key: 'todos',      label: 'Todos',              match: () => true },
  { key: 'en_curso',   label: 'En Cocina',          match: (e) => e === 'CONFIRMADO' || e === 'EN_PREPARACION' },
  { key: 'listos',     label: 'Listos p/ Entregar', match: (e) => e === 'EN_CAMINO' },
  { key: 'entregados', label: 'Entregados',         match: (e) => e === 'ENTREGADO' },
];

// Badge de estado (label + clases Tailwind para celda)
const CAJERO_BADGE: Record<string, { label: string; cls: string }> = {
  CONFIRMADO:     { label: 'En Cocina',  cls: 'bg-blue-500   text-white' },
  EN_PREPARACION: { label: 'Preparando', cls: 'bg-orange-500 text-white' },
  EN_CAMINO:      { label: 'Listo',      cls: 'bg-purple-500 text-white' },
  ENTREGADO:      { label: 'Entregado',  cls: 'bg-green-500  text-white' },
  CANCELADO:      { label: 'Cancelado',  cls: 'bg-red-500    text-white' },
};

// Tinte de fondo de la fila según estado (más sutil que el badge)
const TINTE_FILA: Record<string, string> = {
  CONFIRMADO:     'bg-blue-900/15  hover:bg-blue-900/25',
  EN_PREPARACION: 'bg-orange-900/15 hover:bg-orange-900/25',
  EN_CAMINO:      'bg-purple-900/15 hover:bg-purple-900/25',
  ENTREGADO:      'bg-green-900/10 hover:bg-green-900/20',
  CANCELADO:      'bg-red-900/10   hover:bg-red-900/20',
};

// ─────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────

/** "2× Milanesa, 1× Coca" — resumen compacto para la celda de productos */
function resumenProductos(detalles: DetallePedido[]): string {
  return detalles
    .map((d) => `${d.cantidad}× ${d.nombre_snapshot}`)
    .join(', ');
}

/** Calcula los minutos desde la última transición */
function minutosEnEstado(pedido: Pedido): number {
  const desde = pedido.actualizado_en ?? pedido.creado_en;
  return Math.floor((Date.now() - new Date(desde).getTime()) / 60_000);
}

/** Etiqueta contextual del timer */
function etiquetaTimer(estado: string): string {
  switch (estado) {
    case 'CONFIRMADO':     return 'esperando';
    case 'EN_PREPARACION': return 'preparando';
    case 'EN_CAMINO':      return 'listo';
    case 'ENTREGADO':      return 'entregado';
    default:               return 'hace';
  }
}

/** Color del timer según urgencia */
function timerColor(min: number): string {
  if (min < 5)  return 'text-green-400';
  if (min < 15) return 'text-yellow-400';
  return 'text-red-400';
}

// ─────────────────────────────────────────────────────────────────────
export default function VistaCajero() {
  const { user, isAuthenticated } = useAuthStore();
  const [pedidos,      setPedidos]      = useState<CajeroPedido[]>([]);
  const [loading,      setLoading]      = useState(true);
  const [toast,        setToast]        = useState<{ tipo: 'ok'|'err'; msg: string } | null>(null);
  const [filtroActivo, setFiltroActivo] = useState<FiltroKey>('todos');
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Solo CAJERO (o ADMIN por las dudas) puede entrar
  const isCajero = useMemo(
    () => user?.roles?.some((r) => r.codigo === 'CAJERO' || r.codigo === 'ADMIN') ?? false,
    [user?.roles]
  );

  // Redirigir si no está logueado o no es cajero
  if (!isAuthenticated || !isCajero) {
    return <Navigate to="/admin" replace />;
  }

  // ── Timer global: 1 sola interval para recalcular los timers de las filas ──
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 60_000);
    return () => clearInterval(id);
  }, []);

  // ── Cargar pedidos ─────────────────────────────────────────────────
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

  useEffect(() => {
    cargarPedidos();
  }, [cargarPedidos]);

  // ── Auto-ocultar toast ────────────────────────────────────────────
  useEffect(() => {
    if (!toast) return;
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 4000);
    return () => { if (toastTimer.current) clearTimeout(toastTimer.current); };
  }, [toast]);

  // ── WebSocket ─────────────────────────────────────────────────────
  const handleEvent = useCallback((ev: WSEvent) => {
    if (ev.type === 'pedido.creado') {
      const payload     = ev.payload as { pedido: { id: number; estado_codigo: string } };
      const estadoNuevo = payload.pedido.estado_codigo;
      if (CAJERO_ESTADOS.includes(estadoNuevo as CajeroEstado)) {
        setToast({ tipo: 'ok', msg: '🔔 Nuevo pedido en cocina' });
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

  // ── Conteos por estado (para los tabs de filtro) ──────────────────
  const conteos = useMemo(() => ({
    todos:      pedidos.length,
    en_curso:   pedidos.filter((p) => p.estado_codigo === 'CONFIRMADO' || p.estado_codigo === 'EN_PREPARACION').length,
    listos:     pedidos.filter((p) => p.estado_codigo === 'EN_CAMINO').length,
    entregados: pedidos.filter((p) => p.estado_codigo === 'ENTREGADO').length,
  }), [pedidos]);

  // ── Pedidos filtrados según el tab activo ─────────────────────────
  const pedidosFiltrados = useMemo(() => {
    const filtro = FILTROS.find((f) => f.key === filtroActivo);
    if (!filtro) return pedidos;
    return pedidos.filter((p) => filtro.match(p.estado_codigo));
  }, [pedidos, filtroActivo]);

  // ── Render ────────────────────────────────────────────────────────
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
              {conteos.en_curso} en cocina · {conteos.listos} listos · {conteos.entregados} entregados
            </p>
          </div>
        </div>

        <button
          onClick={cargarPedidos}
          className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded-xl text-sm font-bold transition-colors"
        >
          <Clock className="w-4 h-4" />
          Actualizar
        </button>
      </div>

      {/* ── Toast ─────────────────────────────────────────────────── */}
      {toast && (
        <div
          className={`mb-6 flex items-center gap-3 px-5 py-3 rounded-xl border-2 text-sm font-bold ${
            toast.tipo === 'ok'
              ? 'bg-green-900/60 border-green-500 text-green-300'
              : 'bg-red-900/60 border-red-500 text-red-300'
          }`}
        >
          {toast.tipo === 'ok' ? <CheckCircle2 className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
          {toast.msg}
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
                active
                  ? 'bg-slate-800 text-white border-b-2 border-yellow-500'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
              }`}
            >
              <span>{f.label}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-black ${
                active ? 'bg-yellow-500 text-slate-900' : 'bg-slate-700 text-slate-300'
              }`}>
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* ── Tabla ─────────────────────────────────────────────────── */}
      {pedidosFiltrados.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-slate-500">
          <Banknote className="w-20 h-20 mb-4 opacity-30" />
          <p className="text-2xl font-bold">No hay pedidos {filtroActivo !== 'todos' ? `en "${FILTROS.find(f => f.key === filtroActivo)?.label}"` : 'en el ciclo'}</p>
          <p className="text-sm mt-2">Los pedidos confirmados por el cliente aparecerán aquí automáticamente.</p>
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
                  <th className="px-4 py-3 text-left font-bold">Productos</th>
                  <th className="px-4 py-3 text-left font-bold">Tiempo</th>
                  <th className="px-4 py-3 text-right font-bold">Total</th>
                  <th className="px-4 py-3 text-right font-bold">Acción</th>
                </tr>
              </thead>
              <tbody>
                {pedidosFiltrados.map((p) => (
                  <CajeroRow key={p.id} pedido={p} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Sub-componente: Fila de la tabla
// ─────────────────────────────────────────────────────────────────────
interface CajeroRowProps {
  pedido: CajeroPedido;
}

function CajeroRow({ pedido }: CajeroRowProps) {
  const badge         = CAJERO_BADGE[pedido.estado_codigo] ?? { label: pedido.estado_codigo, cls: 'bg-slate-600' };
  const tinteFila     = TINTE_FILA[pedido.estado_codigo] ?? 'hover:bg-slate-800/50';
  const min           = minutosEnEstado(pedido);

  // Iconito según estado
  const EstadoIcon = pedido.estado_codigo === 'EN_PREPARACION' ? ChefHat :
                     pedido.estado_codigo === 'EN_CAMINO'      ? Truck    :
                     pedido.estado_codigo === 'ENTREGADO'      ? Package  :
                     null;

  return (
    <tr className={`border-b border-slate-800/50 transition-colors ${tinteFila}`}>
      {/* ID */}
      <td className="px-4 py-3">
        <span className="text-lg font-black text-white">#{pedido.id}</span>
      </td>

      {/* Cliente */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-1.5 text-slate-300">
          <User className="w-3.5 h-3.5 text-slate-500" />
          <span className="font-medium">#{pedido.usuario_id}</span>
        </div>
      </td>

      {/* Estado (badge con ícono) */}
      <td className="px-4 py-3">
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-black uppercase ${badge.cls}`}>
          {EstadoIcon && <EstadoIcon className="w-3 h-3" />}
          {badge.label}
        </span>
      </td>

      {/* Pago (oculto en mobile) */}
      <td className="px-4 py-3 text-slate-300 text-xs hidden md:table-cell">
        {pedido.forma_pago_codigo}
      </td>

      {/* Productos (resumen compacto) */}
      <td className="px-4 py-3">
        <div className="max-w-xs truncate text-slate-200" title={resumenProductos(pedido.detalles)}>
          {resumenProductos(pedido.detalles)}
        </div>
      </td>

      {/* Tiempo en estado */}
      <td className="px-4 py-3 whitespace-nowrap">
        <div className={`flex items-center gap-1.5 text-xs font-bold ${timerColor(min)}`}>
          <Timer className="w-3.5 h-3.5" />
          <span>{etiquetaTimer(pedido.estado_codigo)} {min < 1 ? 'recién' : `hace ${min}m`}</span>
        </div>
      </td>

      {/* Total */}
      <td className="px-4 py-3 text-right">
        <span className="text-yellow-400 font-black">
          ${pedido.total.toFixed(2)}
        </span>
      </td>

      {/* Acción */}
      <td className="px-4 py-3">
        <div className="flex items-center justify-end">
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wide">—</span>
        </div>
      </td>
    </tr>
  );
}
