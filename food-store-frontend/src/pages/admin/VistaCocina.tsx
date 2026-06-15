import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { PedidoService, type Pedido } from '../../services/pedido.service';
import { usePedidoEventos } from '../../hooks/usePedidoWebSocket';
import type { WSEvent } from '../../store/wsStore';
import {
  ChefHat, Clock, AlertTriangle, Timer,
  ArrowRight, CheckCircle2, Loader2, User,
  XCircle, StickyNote, Banknote,
} from 'lucide-react';

// Tipo del detalle tal como viene del backend
type DetallePedido = Pedido['detalles'][number];

// Estados que la cocina ve
const COCINA_ESTADOS = ['CONFIRMADO', 'EN_PREPARACION'] as const;
type CocinaEstado = typeof COCINA_ESTADOS[number];

const TIPO_ENTREGA_BADGE: Record<string, { label: string; cls: string }> = {
  EN_LOCAL: { label: 'LOCAL', cls: 'bg-orange-700 text-orange-100' },
  DELIVERY: { label: 'DELIV', cls: 'bg-blue-700   text-blue-100'  },
};

// Badge de estado
const COCINA_BADGE: Record<string, { label: string; cls: string }> = {
  CONFIRMADO:     { label: 'En Cola',  cls: 'bg-yellow-500 text-yellow-950' },
  EN_PREPARACION: { label: 'En Prep.', cls: 'bg-orange-500 text-white' },
};

// Tinte de fondo de la card según estado
const TINTE_CARD: Record<string, string> = {
  CONFIRMADO:     'border-yellow-600/50',
  EN_PREPARACION: 'border-orange-600/50',
};

// Tabs de filtro
type FiltroKey = 'todos' | 'en_cola' | 'en_prep';
const FILTROS: { key: FiltroKey; label: string; match: (e: string) => boolean }[] = [
  { key: 'todos',   label: 'Todos',           match: () => true },
  { key: 'en_cola', label: 'En Cola',        match: (e) => e === 'CONFIRMADO' },
  { key: 'en_prep', label: 'En Preparación', match: (e) => e === 'EN_PREPARACION' },
];

// ─────────────────────────────────────────────────────────────────────
export default function VistaCocina() {
  const { user, isAuthenticated } = useAuthStore();
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [toast, setToast] = useState<{ tipo: 'ok'|'err'; msg: string } | null>(null);
  const [filtroActivo, setFiltroActivo] = useState<FiltroKey>('todos');
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isCocina = useMemo(
    () => user?.roles?.some((r) => r.codigo === 'COCINA' || r.codigo === 'ADMIN') ?? false,
    [user?.roles]
  );

  if (!isAuthenticated || !isCocina) {
    return <Navigate to="/admin" replace />;
  }

  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 30_000);
    return () => clearInterval(id);
  }, []);

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

  useEffect(() => { cargarPedidos(); }, [cargarPedidos]);

  useEffect(() => {
    if (!toast) return;
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 4000);
    return () => { if (toastTimer.current) clearTimeout(toastTimer.current); };
  }, [toast]);

  const handleEvent = useCallback((ev: WSEvent) => {
    if (ev.type === 'pedido.creado') {
      const payload = ev.payload as { pedido: { id: number; estado_codigo: string } };
      if (COCINA_ESTADOS.includes(payload.pedido.estado_codigo as CocinaEstado)) {
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

  const handleAccion = useCallback(async (pedido: Pedido, nuevoEstado: string) => {
    try {
      setUpdatingId(pedido.id);
      await PedidoService.actualizarEstado(pedido.id, nuevoEstado);
      const accionTxt: Record<string, string> = {
        EN_PREPARACION: 'EMPEZÓ',
        EN_CAMINO:      'LISTO',
      };
      setToast({ tipo: 'ok', msg: `Pedido #${pedido.id} → ${accionTxt[nuevoEstado] ?? nuevoEstado}` });
      cargarPedidos();
    } catch {
      setToast({ tipo: 'err', msg: `Error al actualizar el pedido #${pedido.id}` });
    } finally {
      setUpdatingId(null);
    }
  }, [cargarPedidos]);

  const pedidosOrdenados = useMemo(
    () => [...pedidos].sort(
      (a, b) => new Date(a.creado_en).getTime() - new Date(b.creado_en).getTime()
    ),
    [pedidos]
  );

  const conteos = useMemo(() => ({
    todos:   pedidos.length,
    en_cola: pedidos.filter((p) => p.estado_codigo === 'CONFIRMADO').length,
    en_prep: pedidos.filter((p) => p.estado_codigo === 'EN_PREPARACION').length,
  }), [pedidos]);

  const pedidosFiltrados = useMemo(() => {
    const filtro = FILTROS.find((f) => f.key === filtroActivo);
    return pedidosOrdenados.filter((p) => !filtro || filtro.match(p.estado_codigo));
  }, [pedidosOrdenados, filtroActivo]);

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
          <Clock className="w-4 h-4" /> Actualizar
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
      <div className="flex flex-wrap items-center gap-2 mb-6 border-b border-slate-800 pb-1">
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

      {/* ── Cards KDS ─────────────────────────────────────────────── */}
      {pedidosFiltrados.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-slate-500">
          <ChefHat className="w-20 h-20 mb-4 opacity-30" />
          <p className="text-2xl font-bold">
            No hay pedidos{filtroActivo !== 'todos' ? ` en "${FILTROS.find(f => f.key === filtroActivo)?.label}"` : ' en cocina'}
          </p>
          <p className="text-sm mt-2">Los pedidos confirmados aparecerán aquí automáticamente.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {pedidosFiltrados.map((pedido) => (
            <CocinaCard
              key={pedido.id}
              pedido={pedido}
              isLoading={updatingId === pedido.id}
              onAccion={handleAccion}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Card KDS individual
// ─────────────────────────────────────────────────────────────────────
function minutosEnCocina(creadoEn: string): number {
  return Math.floor((Date.now() - new Date(creadoEn).getTime()) / 60_000);
}

function timerColor(min: number): string {
  if (min < 5)  return 'text-green-400';
  if (min < 15) return 'text-yellow-400';
  return 'text-red-400';
}

interface CocinaCardProps {
  pedido: Pedido;
  isLoading: boolean;
  onAccion: (pedido: Pedido, estado: string) => void;
}

function CocinaCard({ pedido, isLoading, onAccion }: CocinaCardProps) {
  const badge = COCINA_BADGE[pedido.estado_codigo] ?? { label: pedido.estado_codigo, cls: 'bg-slate-600' };
  const bordeColor = TINTE_CARD[pedido.estado_codigo] ?? 'border-slate-700';
  const min = minutosEnCocina(pedido.creado_en);
  const isEnCola = pedido.estado_codigo === 'CONFIRMADO';
  const isEnPrep = pedido.estado_codigo === 'EN_PREPARACION';

  return (
    <div className={`bg-slate-800 rounded-2xl border-2 ${bordeColor} overflow-hidden flex flex-col`}>
      {/* ── Header de la card ─────────────────────────────────── */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700/50">
        <div className="flex items-center gap-2">
          <span className="text-2xl font-black text-white">#{pedido.id}</span>
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-black uppercase ${badge.cls}`}>
            {badge.label}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-1 text-xs font-bold ${timerColor(min)}`}>
            <Timer className="w-3.5 h-3.5" />
            <span>{min < 1 ? 'recién' : `${min}m`}</span>
          </div>
          <span className="text-orange-400 font-black text-lg">${pedido.total.toFixed(2)}</span>
        </div>
      </div>

      {/* ── Info del cliente ──────────────────────────────────── */}
      <div className="px-4 py-2 flex items-center gap-3 text-xs text-slate-400 border-b border-slate-700/50 flex-wrap">
        <span className="flex items-center gap-1">
          <User className="w-3.5 h-3.5" /> #{pedido.usuario_id}
        </span>
        <span className="flex items-center gap-1">
          <Banknote className="w-3.5 h-3.5" />
          {pedido.forma_pago_codigo}
        </span>
        {(pedido as any).tipo_entrega && (
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-black uppercase ${
            TIPO_ENTREGA_BADGE[(pedido as any).tipo_entrega]?.cls ?? 'bg-slate-600 text-white'
          }`}>
            {TIPO_ENTREGA_BADGE[(pedido as any).tipo_entrega]?.label ?? (pedido as any).tipo_entrega}
          </span>
        )}
      </div>

      {/* ── Notas del cliente (si hay) ───────────────────────── */}
      {pedido.notas && (
        <div className="mx-4 mt-3 p-3 bg-yellow-900/40 border border-yellow-600/50 rounded-xl flex gap-2">
          <StickyNote className="w-4 h-4 text-yellow-400 shrink-0 mt-0.5" />
          <p className="text-xs text-yellow-200 leading-snug">{pedido.notas}</p>
        </div>
      )}

      {/* ── Lista de productos ─────────────────────────────────── */}
      <div className="flex-1 px-4 py-3 space-y-3">
        {pedido.detalles.map((detalle) => (
          <div key={detalle.producto_id} className="space-y-1">
            {/* Producto principal */}
            <div className="flex items-start gap-2">
              <span className="text-orange-400 font-black text-sm mt-0.5 min-w-[28px]">
                {detalle.cantidad}×
              </span>
              <span className="font-bold text-slate-100 text-sm leading-snug">
                {detalle.nombre_snapshot}
              </span>
            </div>

            {/* Ingredientes removidos */}
            {detalle.personalizacion_nombres && detalle.personalizacion_nombres.length > 0 && (
              <div className="ml-8 flex items-start gap-1.5">
                <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
                <span className="text-red-300 text-xs font-bold leading-snug">
                  Sin: {detalle.personalizacion_nombres.join(', ')}
                </span>
              </div>
            )}

            {/* IDs removidos como fallback (si no vinieron los nombres) */}
            {(!detalle.personalizacion_nombres || detalle.personalizacion_nombres.length === 0) &&
              detalle.personalizacion && detalle.personalizacion.length > 0 && (
              <div className="ml-8 flex items-start gap-1.5">
                <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
                <span className="text-red-300 text-xs font-bold leading-snug">
                  Sin: {detalle.personalizacion.length} ingrediente(s)
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* ── Acciones ─────────────────────────────────────────── */}
      <div className="p-4 border-t border-slate-700/50 flex gap-2">
        {isLoading ? (
          <Loader2 className="w-5 h-5 text-orange-500 animate-spin mx-auto" />
        ) : isEnCola ? (
          <button
            onClick={() => onAccion(pedido, 'EN_PREPARACION')}
            className="flex-1 flex items-center justify-center gap-2 bg-orange-600 hover:bg-orange-500 text-white py-3 rounded-xl font-black text-sm transition-colors"
          >
            🍳 EMPEZAR <ArrowRight className="w-4 h-4" />
          </button>
        ) : isEnPrep ? (
          <button
            onClick={() => onAccion(pedido, 'EN_CAMINO')}
            className="flex-1 flex items-center justify-center gap-2 bg-green-600 hover:bg-green-500 text-white py-3 rounded-xl font-black text-sm transition-colors"
          >
            ✅ LISTO
          </button>
        ) : null}
      </div>
    </div>
  );
}
