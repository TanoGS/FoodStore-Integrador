import { useCallback, useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { PedidoService, type PedidoPublic } from '../../services/pedido.service';
import { usePedidoEventos } from '../../hooks/usePedidoWebSocket';
import type { WSEvent } from '../../store/wsStore';
import {
  ShoppingBag, Clock, ChefHat, Truck, CheckCircle, XCircle, Package,
  CheckCircle2, AlertCircle, X, ChevronLeft, ChevronRight, ChevronDown, ChevronUp,
} from 'lucide-react';

// ── Config de estados ─────────────────────────────────────────────────────────
const ESTADO_CONFIG: Record<string, { label: string; color: string }> = {
  PENDIENTE:       { label: 'Pendiente',       color: 'bg-yellow-100 text-yellow-800' },
  CONFIRMADO:      { label: 'Confirmado',      color: 'bg-blue-100   text-blue-800'   },
  EN_PREPARACION:  { label: 'En preparación',  color: 'bg-orange-100 text-orange-800' },
  EN_CAMINO:       { label: 'En camino',        color: 'bg-purple-100 text-purple-800' },
  ENTREGADO:       { label: 'Entregado',        color: 'bg-green-100  text-green-800'  },
  CANCELADO:       { label: 'Cancelado',        color: 'bg-red-100    text-red-800'    },
};

const ESTADO_ICON: Record<string, React.ElementType> = {
  PENDIENTE: Clock, CONFIRMADO: CheckCircle, EN_PREPARACION: ChefHat,
  EN_CAMINO: Truck, ENTREGADO: Package, CANCELADO: XCircle,
};

// ── Constantes de paginación ───────────────────────────────────────────────────
const PAGE_SIZE = 10;

// ─────────────────────────────────────────────────────────────────────────────
export default function MisPedidos() {
  // ── Estado de paginación ────────────────────────────────────────────────────
  const [page, setPage] = useState(0);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  // ── Server state ────────────────────────────────────────────────────────────
  const { data: result, isLoading, isError } = useQuery<{ data: PedidoPublic[]; total: number }>({
    queryKey: ['mis-pedidos', page],
    queryFn: () => PedidoService.listarMisPedidos({ offset: page * PAGE_SIZE, limit: PAGE_SIZE }),
  });

  const pedidos = result?.data ?? [];
  const total = result?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Para invalidar la query cuando llega un evento del WS
  const queryClient = useQueryClient();

  // Toast de feedback
  type Toast = { tipo: 'ok' | 'err'; msg: string };
  const [toast, setToast] = useState<Toast | null>(null);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(t);
  }, [toast]);

  // ── Suscripción a eventos WebSocket ─────────────────────────────────────────
  const handlePedidoEvent = useCallback((ev: WSEvent) => {
    if (ev.type === 'pedido.mio.actualizado') {
      const payload = ev.payload as { id: number; estado_codigo: string };
      queryClient.invalidateQueries({ queryKey: ['mis-pedidos'] });
      setToast({
        tipo: 'ok',
        msg: `Tu pedido #${payload.id} ahora está "${ESTADO_CONFIG[payload.estado_codigo]?.label ?? payload.estado_codigo}".`,
      });
    } else if (ev.type === 'pedido.creado') {
      queryClient.invalidateQueries({ queryKey: ['mis-pedidos'] });
    }
  }, [queryClient]);

  usePedidoEventos(handlePedidoEvent);

  // ── Handlers ────────────────────────────────────────────────────────────────
  const toggleExpand = (id: number) => {
    setExpandedId(prev => prev === id ? null : id);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    setExpandedId(null); // Cerrar cualquier pedido expandido al cambiar de página
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin h-10 w-10 border-4 border-orange-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen flex items-center justify-center text-red-600 font-bold">
        Error al cargar tus pedidos. Intenta más tarde.
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-black text-slate-800 mb-8 flex items-center gap-2">
        <ShoppingBag className="text-orange-500 w-8 h-8" />
        Mis Pedidos
      </h1>

      {/* Toast de feedback en vivo */}
      {toast && (
        <div
          role="alert"
          className={`mb-6 flex items-start gap-3 p-4 rounded-xl border-2 ${
            toast.tipo === 'ok'
              ? 'bg-green-50 border-green-200 text-green-800'
              : 'bg-red-50 border-red-200 text-red-800'
          }`}
        >
          {toast.tipo === 'ok'
            ? <CheckCircle2 className="w-5 h-5 mt-0.5 shrink-0" />
            : <AlertCircle className="w-5 h-5 mt-0.5 shrink-0" />}
          <p className="font-bold text-sm flex-1">{toast.msg}</p>
          <button
            type="button"
            onClick={() => setToast(null)}
            className="text-current opacity-60 hover:opacity-100 transition-opacity"
            aria-label="Cerrar mensaje"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      {pedidos.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-3xl border border-slate-100 shadow-sm">
          <ShoppingBag className="w-16 h-16 text-slate-300 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-slate-700">Aún no tenés pedidos</h3>
          <Link to="/" className="mt-4 inline-block text-orange-600 font-bold hover:underline">
            Ir al menú
          </Link>
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {pedidos.map((pedido) => {
              const config = ESTADO_CONFIG[pedido.estado_codigo] ?? { label: pedido.estado_codigo, color: 'bg-slate-100 text-slate-700' };
              const Icon = ESTADO_ICON[pedido.estado_codigo] ?? Clock;
              const isExpanded = expandedId === pedido.id;

              return (
                <div key={pedido.id} className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
                  {/* Header del pedido */}
                  <div className="p-5">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <span className="text-xs text-slate-400 font-medium">Pedido</span>
                        <p className="text-xl font-black text-slate-800">#{pedido.id}</p>
                      </div>
                      <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-black uppercase ${config.color}`}>
                        <Icon className="w-3.5 h-3.5" />
                        {config.label}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-sm text-slate-500 border-t border-slate-50 pt-3">
                      <span>
                        {pedido.detalles.length} {pedido.detalles.length === 1 ? 'producto' : 'productos'}
                      </span>
                      <span className="text-lg font-black text-slate-800">
                        ${pedido.total.toFixed(2)}
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 mt-2">
                      {new Date(pedido.creado_en).toLocaleDateString('es-AR', {
                        day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
                      })}
                    </p>

                    {/* Botón ver detalle */}
                    <button
                      type="button"
                      onClick={() => toggleExpand(pedido.id)}
                      className="mt-3 flex items-center gap-1.5 text-sm font-medium text-orange-600 hover:text-orange-700 transition-colors"
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp className="w-4 h-4" />
                          Ocultar productos
                        </>
                      ) : (
                        <>
                          <ChevronDown className="w-4 h-4" />
                          Ver productos
                        </>
                      )}
                    </button>
                  </div>

                  {/* Detalle de productos (expandible) */}
                  {isExpanded && (
                    <div className="border-t border-slate-100 bg-slate-50/50">
                      <div className="p-5">
                        <h4 className="text-sm font-bold text-slate-600 mb-3">Detalle del pedido</h4>
                        <div className="space-y-2">
                          {pedido.detalles.map((detalle, idx) => (
                            <div key={idx} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                              <div className="flex items-center gap-3">
                                <span className="w-8 h-8 rounded-full bg-orange-100 text-orange-700 flex items-center justify-center text-sm font-bold">
                                  {detalle.cantidad}
                                </span>
                              <span className="text-sm font-medium text-slate-700">
                                {detalle.nombre_snapshot}
                              </span>
                              {detalle.personalizacion_nombres && detalle.personalizacion_nombres.length > 0 && (
                                <span className="text-xs text-red-500 font-medium ml-1">
                                  (sin {detalle.personalizacion_nombres.join(', ')})
                                </span>
                              )}
                            </div>
                            <span className="text-sm font-medium text-slate-600">
                              ${detalle.subtotal_snap.toFixed(2)}
                            </span>
                            </div>
                          ))}
                        </div>

                        {/* Resumen de totales */}
                        <div className="mt-4 pt-4 border-t border-slate-200 space-y-1">
                          <div className="flex justify-between text-sm text-slate-500">
                            <span>Subtotal</span>
                            <span>${pedido.subtotal.toFixed(2)}</span>
                          </div>
                          {pedido.descuento > 0 && (
                            <div className="flex justify-between text-sm text-green-600">
                              <span>Descuento</span>
                              <span>-${pedido.descuento.toFixed(2)}</span>
                            </div>
                          )}
                          {pedido.costo_envio > 0 && (
                            <div className="flex justify-between text-sm text-slate-500">
                              <span>Envío</span>
                              <span>${pedido.costo_envio.toFixed(2)}</span>
                            </div>
                          )}
                          <div className="flex justify-between text-base font-bold text-slate-800 pt-2 border-t border-slate-200">
                            <span>Total</span>
                            <span>${pedido.total.toFixed(2)}</span>
                          </div>
                        </div>

                        {/* Forma de pago */}
                        <div className="mt-3 text-xs text-slate-400">
                          Pago: {pedido.forma_pago_codigo}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Controles de paginación */}
          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-4">
              <button
                type="button"
                onClick={() => handlePageChange(page - 1)}
                disabled={page === 0}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-xl font-medium text-sm transition-colors ${
                  page === 0
                    ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                    : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                }`}
              >
                <ChevronLeft className="w-4 h-4" />
                Anterior
              </button>

              <div className="flex items-center gap-2">
                {Array.from({ length: totalPages }, (_, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => handlePageChange(i)}
                    className={`w-10 h-10 rounded-xl font-bold text-sm transition-colors ${
                      i === page
                        ? 'bg-orange-500 text-white'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {i + 1}
                  </button>
                ))}
              </div>

              <button
                type="button"
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= totalPages - 1}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-xl font-medium text-sm transition-colors ${
                  page >= totalPages - 1
                    ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                    : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                }`}
              >
                Siguiente
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Info de paginación */}
          {totalPages > 1 && (
            <p className="mt-4 text-center text-sm text-slate-500">
              Mostrando {page * PAGE_SIZE + 1} - {Math.min((page + 1) * PAGE_SIZE, total)} de {total} pedidos
            </p>
          )}
        </>
      )}
    </div>
  );
}