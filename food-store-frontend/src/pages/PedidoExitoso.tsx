import { useParams, Link } from 'react-router-dom';
import { CheckCircle, ShoppingBag, Home } from 'lucide-react';

export default function PedidoExitoso() {
  // useParams extrae el segmento dinámico :pedidoId de la URL
  const { pedidoId } = useParams<{ pedidoId: string }>();

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-3xl shadow-sm border border-slate-100 p-12 max-w-md w-full text-center">

        <div className="flex justify-center mb-6">
          <CheckCircle className="w-20 h-20 text-green-500" />
        </div>

        <h1 className="text-3xl font-black text-slate-800 mb-2">
          ¡Pedido confirmado!
        </h1>

        <p className="text-slate-500 mb-4">
          Tu pedido fue recibido y está siendo procesado.
        </p>

        {/* Muestra el ID dinámico obtenido con useParams */}
        <div className="bg-slate-50 rounded-2xl p-4 mb-8">
          <p className="text-sm text-slate-400 font-medium">Número de pedido</p>
          <p className="text-4xl font-black text-orange-600 mt-1">#{pedidoId}</p>
        </div>

        <div className="flex flex-col gap-3">
          <Link
            to="/"
            className="flex items-center justify-center gap-2 bg-orange-600 hover:bg-orange-700 text-white px-6 py-3 rounded-xl font-bold transition-colors"
          >
            <Home className="w-5 h-5" /> Volver al inicio
          </Link>
          <Link
            to="/"
            className="flex items-center justify-center gap-2 border border-slate-200 text-slate-600 hover:bg-slate-50 px-6 py-3 rounded-xl font-bold transition-colors"
          >
            <ShoppingBag className="w-5 h-5" /> Seguir comprando
          </Link>
        </div>

      </div>
    </div>
  );
}
