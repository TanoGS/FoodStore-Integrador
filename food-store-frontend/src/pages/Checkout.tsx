import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useCartStore } from '../store/cartStore';
import { useAuthStore } from '../store/authStore';
import { DireccionService, type Direccion } from '../services/direccion.service';
import { PedidoService } from '../services/pedido.service';
import { MapPin, ShoppingBag, CreditCard, ArrowLeft, Loader2, Plus } from 'lucide-react';

export default function Checkout() {
  const { items, getTotalPrice, clearCart } = useCartStore();
  const { isAuthenticated } = useAuthStore();
  const navigate = useNavigate();

  const [direcciones, setDirecciones] = useState<Direccion[]>([]);
  const [direccionId, setDireccionId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login?redirect=checkout');
      return;
    }

    if (items.length === 0) {
      navigate('/');
      return;
    }

    const cargarDatos = async () => {
      try {
        const data = await DireccionService.listar();
        setDirecciones(data);
        // Seleccionamos la predeterminada por defecto
        const principal = data.find((d: Direccion) => d.predeterminada);
        if (principal) setDireccionId(principal.id);
        else if (data.length > 0) setDireccionId(data[0].id);
      } catch (error) {
        console.error("Error al cargar direcciones", error);
      } finally {
        setLoading(false);
      }
    };

    cargarDatos();
  }, [isAuthenticated, items.length, navigate]);

  const handleFinalizarPedido = async () => {
    if (!direccionId) {
      alert("Por favor, selecciona una dirección de entrega.");
      return;
    }

    try {
      setIsSubmitting(true);
      
      // Preparamos los items para el backend (solo id y cantidad)
      const itemsPayload = items.map(it => ({
        producto_id: it.producto.id,
        cantidad: it.cantidad
      }));

      const pedidoCreado = await PedidoService.crear({
        direccion_id: direccionId,
        items: itemsPayload
      });

      // ¡Éxito! Limpiamos carrito y vamos a confirmación
      clearCart();
      // Nota: Según tu guía, MercadoPago va al final. 
      // Por ahora redirigimos a una página de éxito simple.
      navigate(`/pedido-exitoso/${pedidoCreado.id}`);

    } catch (error) {
      console.error("Error al crear el pedido", error);
      alert("Hubo un error al procesar tu pedido. Intenta nuevamente.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <Loader2 className="w-10 h-10 animate-spin text-orange-600" />
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4">
      <div className="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* COLUMNA IZQUIERDA: Formulario */}
        <div className="lg:col-span-2 space-y-6">
          <Link to="/" className="flex items-center gap-2 text-slate-500 hover:text-orange-600 transition-colors mb-4">
            <ArrowLeft className="w-4 h-4" /> Volver al catálogo
          </Link>

          <h1 className="text-3xl font-black text-slate-800">Finalizar Pedido</h1>

          {/* Sección 1: Dirección */}
          <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
            <div className="flex items-center gap-3 mb-6">
              <div className="bg-orange-100 p-2 rounded-xl text-orange-600">
                <MapPin className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-bold text-slate-800">Dirección de Entrega</h2>
            </div>

            {direcciones.length === 0 ? (
              <div className="text-center py-6 border-2 border-dashed border-slate-200 rounded-2xl">
                <p className="text-slate-500 mb-4">No tienes direcciones registradas</p>
                <Link to="/mis-direcciones" className="inline-flex items-center gap-2 bg-slate-900 text-white px-6 py-2 rounded-xl font-bold">
                  <Plus className="w-4 h-4" /> Agregar Dirección
                </Link>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {direcciones.map((dir) => (
                  <label 
                    key={dir.id}
                    className={`relative flex items-center p-4 rounded-2xl border-2 cursor-pointer transition-all ${
                      direccionId === dir.id ? 'border-orange-500 bg-orange-50/30' : 'border-slate-100 hover:border-slate-200'
                    }`}
                  >
                    <input 
                      type="radio" 
                      name="direccion" 
                      className="hidden" 
                      onChange={() => setDireccionId(dir.id)}
                      checked={direccionId === dir.id}
                    />
                    <div className="flex-1">
                      <p className="font-bold text-slate-800">{dir.calle} {dir.numero}</p>
                      <p className="text-sm text-slate-500">{dir.ciudad} · CP {dir.codigo_postal}</p>
                    </div>
                    {direccionId === dir.id && (
                      <div className="bg-orange-500 rounded-full p-1 text-white">
                        <Loader2 className="w-4 h-4" /> {/* Puedes usar un Check icon aquí */}
                      </div>
                    )}
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Sección 2: Pago (Simulado por ahora) */}
          <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100 opacity-60 grayscale">
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-slate-100 p-2 rounded-xl text-slate-600">
                <CreditCard className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-bold text-slate-800">Método de Pago</h2>
            </div>
            <p className="text-sm text-slate-500 italic">La integración con MercadoPago estará disponible próximamente. El pedido se registrará como "Pendiente".</p>
          </div>
        </div>

        {/* COLUMNA DERECHA: Resumen (Sticky) */}
        <div className="lg:col-span-1">
          <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100 sticky top-8">
            <div className="flex items-center gap-2 mb-6">
              <ShoppingBag className="w-5 h-5 text-slate-400" />
              <h2 className="text-lg font-bold text-slate-800">Resumen del pedido</h2>
            </div>

            <div className="space-y-4 mb-8 max-h-60 overflow-y-auto pr-2">
              {items.map((item) => (
                <div key={item.producto.id} className="flex justify-between text-sm">
                  <span className="text-slate-600">
                    <span className="font-bold text-slate-800">{item.cantidad}x</span> {item.producto.nombre}
                  </span>
                  <span className="font-bold text-slate-800">${item.producto.precio_base * item.cantidad}</span>
                </div>
              ))}
            </div>

            <div className="border-t border-slate-100 pt-6 space-y-4">
              <div className="flex justify-between items-center text-slate-500">
                <span>Subtotal</span>
                <span>${getTotalPrice()}</span>
              </div>
              <div className="flex justify-between items-center text-slate-500">
                <span>Envío</span>
                <span className="text-green-600 font-bold">¡Gratis!</span>
              </div>
              <div className="flex justify-between items-center pt-2">
                <span className="text-xl font-black text-slate-800">Total</span>
                <span className="text-2xl font-black text-orange-600">${getTotalPrice()}</span>
              </div>
            </div>

            <button
              onClick={handleFinalizarPedido}
              disabled={isSubmitting || !direccionId}
              className="w-full bg-slate-900 hover:bg-orange-600 disabled:bg-slate-300 text-white py-4 rounded-2xl font-black text-lg mt-8 transition-all shadow-lg active:scale-95 flex justify-center items-center gap-2"
            >
              {isSubmitting ? (
                <> <Loader2 className="w-6 h-6 animate-spin" /> Procesando... </>
              ) : (
                "CONFIRMAR Y PAGAR"
              )}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}