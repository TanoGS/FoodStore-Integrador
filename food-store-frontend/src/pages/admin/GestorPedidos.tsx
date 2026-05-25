import { useState, useEffect, type ElementType } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { PedidoService, type Pedido } from '../../services/pedido.service';
import { ClipboardList, Clock, CheckCircle, ChefHat, Truck, Package, XCircle } from 'lucide-react';

interface EstadoUIConfig {
  color: string;
  icon: ElementType;
}

// Diccionario para los colores e íconos de la Máquina de Estados
const ESTADOS_UI: Record<string, EstadoUIConfig> = {
  'PENDIENTE': { color: 'bg-yellow-100 text-yellow-800', icon: Clock },
  'CONFIRMADO': { color: 'bg-blue-100 text-blue-800', icon: CheckCircle },
  'EN_PREPARACION': { color: 'bg-orange-100 text-orange-800', icon: ChefHat },
  'EN_CAMINO': { color: 'bg-purple-100 text-purple-800', icon: Truck },
  'ENTREGADO': { color: 'bg-green-100 text-green-800', icon: Package },
  'CANCELADO': { color: 'bg-red-100 text-red-800', icon: XCircle }
};

export default function GestorPedidos() {
  const { user, isAuthenticated } = useAuthStore();
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [loading, setLoading] = useState(true);

  // RBAC: verifica que al menos un rol del usuario tenga permiso de gestión
  const canManageOrders = user?.roles?.some(
    (r) => r.codigo === 'ADMIN' || r.codigo === 'GESTOR_PEDIDOS'
  ) ?? false;

  useEffect(() => {
    if (canManageOrders) {
      cargarPedidos();
    }
  }, [canManageOrders]);

  const cargarPedidos = async () => {
    try {
      setLoading(true);
      const data = await PedidoService.listarTodos();
      // Ordenamos para que los más nuevos salgan arriba
      setPedidos(data.sort((a, b) => b.id - a.id));
    } catch (error) {
      console.error("Error al cargar pedidos:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleCambiarEstado = async (id: number, nuevoEstado: string) => {
    try {
      await PedidoService.actualizarEstado(id, nuevoEstado);
      // Recargamos la lista para ver el cambio
      cargarPedidos();
    } catch (error) {
      console.error("Error al cambiar estado:", error);
      alert("No se pudo cambiar el estado. Verifica las reglas de transición (FSM).");
    }
  };

  // Si no está logueado o no tiene el rol correcto, lo mandamos al inicio
  if (!isAuthenticated || !canManageOrders) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-7xl mx-auto">
        
        <div className="flex items-center gap-4 mb-8 border-b border-slate-200 pb-6">
          <div className="bg-slate-900 p-3 rounded-xl text-white">
            <ClipboardList className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-3xl font-black text-slate-800 tracking-tight">Gestor de Pedidos</h1>
            <p className="text-slate-500">Administra el ciclo de vida de las órdenes (FSM).</p>
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
          </div>
        ) : (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 text-sm uppercase tracking-wider">
                  <th className="p-4 font-bold">ID Pedido</th>
                  <th className="p-4 font-bold">Fecha</th>
                  <th className="p-4 font-bold">Total</th>
                  <th className="p-4 font-bold">Estado Actual</th>
                  <th className="p-4 font-bold text-right">Acciones (Transición)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pedidos.map((pedido) => {
                  const UI = ESTADOS_UI[pedido.estado] || ESTADOS_UI['PENDIENTE'];
                  const Icono = UI.icon;

                  return (
                    <tr key={pedido.id} className="hover:bg-slate-50 transition-colors">
                      <td className="p-4 font-black text-slate-700">#{pedido.id}</td>
                      <td className="p-4 text-slate-500 text-sm">
                        {new Date(pedido.fecha_creacion).toLocaleString()}
                      </td>
                      <td className="p-4 font-bold text-slate-800">${pedido.total}</td>
                      <td className="p-4">
                        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${UI.color}`}>
                          <Icono className="w-4 h-4" />
                          {pedido.estado.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="p-4 text-right">
                        {/* Dropdown simple para cambiar estados */}
                        <select 
                          className="bg-slate-100 border border-slate-200 text-slate-700 text-sm rounded-lg focus:ring-slate-500 focus:border-slate-500 block p-2.5 ml-auto outline-none"
                          value={pedido.estado}
                          onChange={(e) => handleCambiarEstado(pedido.id, e.target.value)}
                        >
                          <option value="PENDIENTE">Pendiente</option>
                          <option value="CONFIRMADO">Confirmado</option>
                          <option value="EN_PREPARACION">En Preparación</option>
                          <option value="EN_CAMINO">En Camino</option>
                          <option value="ENTREGADO">Entregado</option>
                          <option value="CANCELADO">Cancelar</option>
                        </select>
                      </td>
                    </tr>
                  );
                })}
                {pedidos.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-slate-400">
                      No hay pedidos registrados en el sistema.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}