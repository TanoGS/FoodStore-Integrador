import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { PedidoService, type PedidoPublic } from '../../services/pedido.service';
import { ShoppingBag, Clock, ChefHat, Truck, CheckCircle, XCircle, Package } from 'lucide-react';

// Mapa visual de estados (igual que en GestorPedidos pero para el cliente)
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

export default function MisPedidos() {
  // ── SERVER STATE: listado de pedidos del usuario logueado ──────────────────
  const { data: pedidos = [], isLoading, isError } = useQuery<PedidoPublic[]>({
    queryKey: ['mis-pedidos'],
    queryFn: PedidoService.listarMisPedidos,
  });

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
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-black text-slate-800 mb-8 flex items-center gap-2">
        <ShoppingBag className="text-orange-500 w-8 h-8" />
        Mis Pedidos
      </h1>

      {pedidos.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-3xl border border-slate-100 shadow-sm">
          <ShoppingBag className="w-16 h-16 text-slate-300 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-slate-700">Aún no tenés pedidos</h3>
          <Link to="/" className="mt-4 inline-block text-orange-600 font-bold hover:underline">
            Ir al menú
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {pedidos.map((pedido) => {
            const config = ESTADO_CONFIG[pedido.estado_codigo] ?? { label: pedido.estado_codigo, color: 'bg-slate-100 text-slate-700' };
            const Icon = ESTADO_ICON[pedido.estado_codigo] ?? Clock;

            return (
              <div key={pedido.id} className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
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
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
