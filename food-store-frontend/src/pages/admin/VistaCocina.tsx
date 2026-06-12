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
  ChefHat, Clock, AlertTriangle, Timer,
  ArrowRight, CheckCircle2, Loader2, User,
} from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────
// Tipos y config
// ─────────────────────────────────────────────────────────────────────
type CocinaPedido = Pedido;

// Estados que la cocina ve: cola y en preparación
const COCINA_ESTADOS = ['CONFIRMADO', 'EN_PREPARACION'] as const;
type CocinaEstado = typeof COCINA_ESTADOS[number];

// Badge de estado dentro de la vista cocina
const COCINA_BADGE: Record<string, { label: string; cls: string }> = {
  CONFIRMADO:     { label: 'En Cola',  cls: 'bg-yellow-500 text-yellow-950' },
  EN_PREPARACION: { label: 'En Prep.', cls: 'bg-orange-500 text-white' },
};

// Tinte de fondo de la fila según estado (más sutil que el badge)
const TINTE_FILA: Record<string, string> = {
  CONFIRMADO:     'bg-yellow-900/15 hover:bg-yellow-900/25',
  EN_PREPARACION: 'bg-orange-900/15 hover:bg-orange-900/25',
};

// Tabs de filtro
type FiltroKey = 'todos' | 'en_cola' | 'en_prep';
const FILTROS: { key: FiltroKey; label: string; match: (e: string) => boolean }[] = [
  { key: 'todos',   label: 'Todos',          match: () => true },
  { key: 'en_cola', label: 'En Cola',        match: (e) => e === 'CONFIRMADO' },
  { key: 'en_prep', label: 'En Preparación', match: (e) => e === 'EN_PREPARACION' },
];

// ─────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────

/** "2× Milanesa, 1× Coca" — resumen compacto para la celda de productos */
function resumenProductos(detalles: DetallePedido[]): string {
  return detalles
    .map((d) => `${d.cantidad}× ${d.nombre_snapshot}`)
    .join(', ');
}

/**
 * Minutos desde que el pedido entró a la cocina.
 * En el flujo actual, `creado_en` coincide con el momento en que el
 * backend dejó el pedido en CONFIRMADO (entró a la cola de cocina).
 * A diferencia del cajero, acá NO reseteamos al cambiar de estado:
 * la cocina quiere saber cuánto lleva esperando el pedido en total.
 */
function minutosEnCocina(pedido: Pedido): number {
  return Math.floor((Date.now() - new Date(pedido.creado_en).getTime()) / 60_000);
}

/** Color del timer según urgencia */
function timerColor(min: number): string {
  if (min < 5)  return 'text-green-400';
  if (min < 15) return 'text-yellow-400';
  return 'text-red-400';
}

// ─────────────────────────────────────────────────────────────────────
export default function VistaCocina() {
  const { user, isAuthenticated } = useAuthStore();
  const [pedidos,      setPedidos]      = useState<CocinaPedido[]>([]);
  const [loading,      setLoading]      = useState(true);
  const [updatingId,   setUpdatingId]   = useState<number | null>(null);
  const [toast,        setToast]        = useState<{ tipo: 'ok'|'err'; msg: string } | null>(null);
  const [filtroActivo, setFiltroActivo] = useState<FiltroKey>('todos');
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Solo COCINA puede entrar
  const isCocina = useMemo(
    () => user?.roles?.some((r) => r.codigo === 'COCINA' || r.codigo === 'ADMIN') ?? false,
    [user?.roles]
  );

  // Redirigir si no es staff o no es cocina
  if (!isAuthenticated || !isCocina) {
    return <Navigate to="/admin" replace />;
  }

  // ── Cargar pedidos de cocina ──────────────────────────────────────
  const cargarPedidos = useCallback(async () => {
    try {
      const todos = await PedidoService.listarTodos();
      setPedidos(todos.filter((p) => COCINA_ESTADOS.includes(p.estado_codigo as CocinaEstado)));
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

  // ── WebSocket: eventos en tiempo real ─────────────────────────────
  const handleEvent = useCallback((ev: WSEvent) => {
    if (ev.type === 'pedido.creado') {
      const payload     = ev.payload as { pedido: { id: number; estado_codigo: string } };
      const estadoNuevo = payload.pedido.estado_codigo;
      if (COCINA_ESTADOS.includes(estadoNuevo as CocinaEstado)) {
        setToast({ tipo: 'ok', msg: '🔔 Nuevo pedido en cocina' });
        cargarPedidos();
      }
    } else if (ev.type === 'pedido.estado.cambiado') {
      const payload = ev.payload as { estado_hacia: string; pedido: { id: number } };
      if (COCINA_ESTADOS.includes(payload.estado_hacia as CocinaEstado)) {
        cargarPedidos();
      } else {
        setPedidos((prev) => prev.filter((p) => p.id !== payload.pedido.id));
      }
    }
  }, [cargarPedidos]);

  usePedidoEventos(handleEvent);

  // ── Acciones: solo avanzar estado (no se cancela desde cocina) ──
  const handleAccion = useCallback(async (pedido: CocinaPedido, nuevoEstado: string) => {
    try {
      setUpdatingId(pedido.id);
      await PedidoService.actualizarEstado(pedido.id, nuevoEstado);
      const accionTxt: Record<string, string> = {
        EN_PREPARACION: 'EMPEZAR',
        EN_CAMINO:      'LISTO',
      };
      setToast({
        tipo: 'ok',
        msg: `Pedido #${pedido.id} → ${accionTxt[nuevoEstado] ?? nuevoEstado}`,
      });
      cargarPedidos();
    } catch {
      setToast({ tipo: 'err', msg: `Error al actualizar el pedido #${pedido.id}` });
    } finally {
      setUpdatingId(null);
    }
  }, [cargarPedidos]);

  // ── Timer global: 1 sola interval para recalcular los timers de las filas ──
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 60_000);
    return () => clearInterval(id);
  }, []);

  // ── Pedidos ordenados por antigüedad (los más viejos arriba) ──────
  const pedidosOrdenados = useMemo(
    () => [...pedidos].sort(
      (a, b) => new Date(a.creado_en).getTime() - new Date(b.creado_en).getTime()
    ),
    [pedidos]
  );

  // ── Conteos por estado (para los tabs de filtro) ──────────────────
  const conteos = useMemo(() => ({
    todos:   pedidos.length,
    en_cola: pedidos.filter((p) => p.estado_codigo === 'CONFIRMADO').length,
    en_prep: pedidos.filter((p) => p.estado_codigo === 'EN_PREPARACION').length,
  }), [pedidos]);

  // ── Pedidos filtrados según el tab activo ─────────────────────────
  const pedidosFiltrados = useMemo(() => {
    const filtro = FILTROS.find((f) => f.key === filtroActivo);
    if (!filtro) return pedidosOrdenados;
    return pedidosOrdenados.filter((p) => filtro.match(p.estado_codigo));
  }, [pedidosOrdenados, filtroActivo]);

  // ── Render ────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <Loader2 className="w-12 h-12 text-orange-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white p-6">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="bg-orange-600 p-3 rounded-2xl">
            <ChefHat className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-3xl font-black tracking-tight">COCINA</h1>
            <p className="text-orange-400 text-sm font-medium">
              {conteos.en_cola} en cola · {conteos.en_prep} en preparación
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
                  ? 'bg-slate-800 text-white border-b-2 border-orange-500'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
              }`}
            >
              <span>{f.label}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-black ${
                active ? 'bg-orange-500 text-slate-900' : 'bg-slate-700 text-slate-300'
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
          <ChefHat className="w-20 h-20 mb-4 opacity-30" />
          <p className="text-2xl font-bold">No hay pedidos {filtroActivo !== 'todos' ? `en "${FILTROS.find(f => f.key === filtroActivo)?.label}"` : 'en cocina'}</p>
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
                  <th className="px-4 py-3 text-left font-bold">Productos</th>
                  <th className="px-4 py-3 text-left font-bold">Tiempo</th>
                  <th className="px-4 py-3 text-right font-bold">Total</th>
                  <th className="px-4 py-3 text-right font-bold">Acción</th>
                </tr>
              </thead>
              <tbody>
                {pedidosFiltrados.map((p) => (
                  <CocinaRow
                    key={p.id}
                    pedido={p}
                    isLoading={updatingId === p.id}
                    onAccion={handleAccion}
                  />
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
interface CocinaRowProps {
  pedido:          CocinaPedido;
  isLoading:        boolean;
  onAccion:         (pedido: CocinaPedido, estado: string) => void;
}

function CocinaRow({ pedido, isLoading, onAccion }: CocinaRowProps) {
  const badge     = COCINA_BADGE[pedido.estado_codigo] ?? { label: pedido.estado_codigo, cls: 'bg-slate-600' };
  const tinteFila = TINTE_FILA[pedido.estado_codigo] ?? 'hover:bg-slate-800/50';
  const isEnCola  = pedido.estado_codigo === 'CONFIRMADO';
  const isEnPrep  = pedido.estado_codigo === 'EN_PREPARACION';
  const min       = minutosEnCocina(pedido);

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

      {/* Estado (badge) */}
      <td className="px-4 py-3">
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-black uppercase ${badge.cls}`}>
          {badge.label}
        </span>
      </td>

      {/* Productos (resumen compacto) */}
      <td className="px-4 py-3">
        <div className="max-w-xs truncate text-slate-200" title={resumenProductos(pedido.detalles)}>
          {resumenProductos(pedido.detalles)}
        </div>
      </td>

      {/* Tiempo en cocina (desde creado_en) */}
      <td className="px-4 py-3 whitespace-nowrap">
        <div className={`flex items-center gap-1.5 text-xs font-bold ${timerColor(min)}`}>
          <Timer className="w-3.5 h-3.5" />
          <span>{min < 1 ? 'recién' : `hace ${min}m`}</span>
        </div>
      </td>

      {/* Total */}
      <td className="px-4 py-3 text-right">
        <span className="text-orange-400 font-black">
          ${pedido.total.toFixed(2)}
        </span>
      </td>

      {/* Acción */}
      <td className="px-4 py-3">
        <div className="flex items-center justify-end gap-2">
          {isLoading ? (
            <Loader2 className="w-4 h-4 text-orange-500 animate-spin" />
          ) : isEnCola ? (
            <button
              onClick={() => onAccion(pedido, 'EN_PREPARACION')}
              className="flex items-center gap-1.5 bg-orange-600 hover:bg-orange-500 text-white px-3 py-1.5 rounded-lg text-xs font-black transition-colors"
            >
              🍳 EMPEZAR
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          ) : isEnPrep ? (
            <button
              onClick={() => onAccion(pedido, 'EN_CAMINO')}
              className="flex items-center gap-1.5 bg-green-600 hover:bg-green-500 text-white px-3 py-1.5 rounded-lg text-xs font-black transition-colors"
            >
              ✅ LISTO
              <CheckCircle2 className="w-3.5 h-3.5" />
            </button>
          ) : (
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wide">—</span>
          )}
        </div>
      </td>
    </tr>
  );
}
