import { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import {
  CheckCircle, Clock, XCircle, ShoppingBag, Home, ListOrdered, Loader2,
  ExternalLink, AlertTriangle,
} from 'lucide-react';
import { PagosService, type PagoResponse } from '../services/pagos.service';

type EstadoPago = 'loading' | 'approved' | 'pending' | 'rejected' | 'error';

export default function PedidoExitoso() {
  const { pedidoId } = useParams<{ pedidoId: string }>();
  const [searchParams] = useSearchParams();
  const statusFromMP = searchParams.get('status'); // ?status=approved|pending|rejected

  const [pago, setPago] = useState<PagoResponse | null>(null);
  const [estado, setEstado] = useState<EstadoPago>(statusFromMP as EstadoPago || 'loading');

  // Consultar el pago al backend para confirmar el estado real
  useEffect(() => {
    if (!pedidoId) return;

    const fetchPago = async () => {
      try {
        const data = await PagosService.obtenerPorPedido(Number(pedidoId));
        setPago(data);
        // Mapear mp_status al estado local
        if (data.mp_status === 'approved') setEstado('approved');
        else if (data.mp_status === 'rejected' || data.mp_status === 'cancelled') setEstado('rejected');
        else setEstado('pending');
      } catch (err) {
        // No hay pago registrado aún → asumimos pending (puede estar esperando webhook)
        setEstado(statusFromMP as EstadoPago || 'pending');
      }
    };

    fetchPago();
  }, [pedidoId, statusFromMP]);

  // ── Configuración visual según estado ──
  const configs: Record<EstadoPago, {
    icon: any; iconColor: string; bgColor: string;
    title: string; subtitle: string; badge: string; badgeClass: string;
  }> = {
    approved: {
      icon: CheckCircle, iconColor: 'text-green-500', bgColor: 'bg-green-50',
      title: '¡Pago aprobado!', subtitle: 'Tu pedido fue confirmado y se está preparando.',
      badge: 'APROBADO', badgeClass: 'bg-green-100 text-green-700',
    },
    pending: {
      icon: Clock, iconColor: 'text-yellow-500', bgColor: 'bg-yellow-50',
      title: 'Pago pendiente', subtitle: 'Estamos esperando la confirmación de MercadoPago.',
      badge: 'EN PROCESO', badgeClass: 'bg-yellow-100 text-yellow-700',
    },
    rejected: {
      icon: XCircle, iconColor: 'text-red-500', bgColor: 'bg-red-50',
      title: 'Pago rechazado', subtitle: 'No se pudo procesar el pago. Podés intentar de nuevo.',
      badge: 'RECHAZADO', badgeClass: 'bg-red-100 text-red-700',
    },
    loading: {
      icon: Loader2, iconColor: 'text-blue-500 animate-spin', bgColor: 'bg-blue-50',
      title: 'Verificando pago...', subtitle: 'Consultando el estado en MercadoPago.',
      badge: 'CARGANDO', badgeClass: 'bg-blue-100 text-blue-700',
    },
    error: {
      icon: AlertTriangle, iconColor: 'text-orange-500', bgColor: 'bg-orange-50',
      title: 'No se pudo verificar el pago',
      subtitle: 'Tu pedido fue creado pero no pudimos confirmar el pago.',
      badge: 'ERROR', badgeClass: 'bg-orange-100 text-orange-700',
    },
  };

  const config = configs[estado] || configs.approved;
  const Icon = config.icon;

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4 py-12">
      <div className="bg-white rounded-3xl shadow-sm border border-slate-100 p-12 max-w-md w-full text-center">

        <div className={`flex justify-center mb-6 ${config.bgColor} w-24 h-24 rounded-full mx-auto`}>
          <Icon className={`w-12 h-12 ${config.iconColor} my-auto`} />
        </div>

        <span className={`inline-block ${config.badgeClass} text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full mb-3`}>
          {config.badge}
        </span>

        <h1 className="text-3xl font-black text-slate-800 mb-2">
          {config.title}
        </h1>

        <p className="text-slate-500 mb-6">
          {config.subtitle}
        </p>

        {/* Info del pedido */}
        <div className="bg-slate-50 rounded-2xl p-4 mb-4">
          <p className="text-sm text-slate-400 font-medium">Número de pedido</p>
          <p className="text-4xl font-black text-orange-600 mt-1">#{pedidoId}</p>
        </div>

        {/* Info del pago (si está disponible) */}
        {pago && (
          <div className="bg-blue-50/50 border border-blue-100 rounded-2xl p-4 mb-6 text-left">
            <p className="text-[10px] font-black uppercase tracking-wider text-blue-700 mb-2">
              Detalle del pago
            </p>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Monto:</span>
                <span className="font-bold text-slate-800">${pago.transaction_amount}</span>
              </div>
              {pago.payment_method_id && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Método:</span>
                  <span className="font-bold text-slate-800 uppercase">{pago.payment_method_id}</span>
                </div>
              )}
              {pago.mp_status_detail && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Detalle:</span>
                  <span className="font-bold text-slate-800 text-xs">{pago.mp_status_detail}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-slate-500">Ref. externa:</span>
                <span className="font-mono text-xs text-slate-600 truncate ml-2">
                  {pago.external_reference.slice(0, 8)}...
                </span>
              </div>
            </div>
          </div>
        )}

        <div className="flex flex-col gap-3">
          {estado === 'rejected' && (
            <Link
              to="/checkout"
              className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-bold transition-colors"
            >
              <ExternalLink className="w-5 h-5" /> Reintentar el pago
            </Link>
          )}
          <Link
            to="/mis-pedidos"
            className="flex items-center justify-center gap-2 bg-orange-600 hover:bg-orange-700 text-white px-6 py-3 rounded-xl font-bold transition-colors"
          >
            <ListOrdered className="w-5 h-5" /> Ver mis pedidos
          </Link>
          <Link
            to="/"
            className="flex items-center justify-center gap-2 border border-slate-200 text-slate-600 hover:bg-slate-50 px-6 py-3 rounded-xl font-bold transition-colors"
          >
            <ShoppingBag className="w-5 h-5" /> Seguir comprando
          </Link>
          <Link
            to="/"
            className="inline-flex items-center justify-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors"
          >
            <Home className="w-3 h-3" /> Volver al inicio
          </Link>
        </div>

      </div>
    </div>
  );
}
