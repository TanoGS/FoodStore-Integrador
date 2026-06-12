import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useCartStore } from '../store/cartStore';
import { useAuthStore } from '../store/authStore';
import { DireccionService, type Direccion } from '../services/direccion.service';
import { PedidoService } from '../services/pedido.service';
import { PagosService } from '../services/pagos.service';
import {
  MapPin, ShoppingBag, CreditCard, ArrowLeft, Loader2, Plus,
  Banknote, ArrowRightLeft, Smartphone, Check, Clock, ExternalLink,
} from 'lucide-react';

type FormaPagoCodigo = 'EFECTIVO' | 'TRANSFERENCIA' | 'MERCADOPAGO';

interface FormaPagoItem {
  codigo: FormaPagoCodigo;
  label: string;
  icon: React.ElementType;
  desc: string;
  habilitada: boolean;
}

const FORMAS_PAGO: FormaPagoItem[] = [
  { codigo: 'EFECTIVO',      label: 'Efectivo',      icon: Banknote,       desc: 'Pagás al recibir el pedido',     habilitada: false },
  { codigo: 'TRANSFERENCIA', label: 'Transferencia', icon: ArrowRightLeft, desc: 'Te pasamos el CBU al confirmar', habilitada: false },
  { codigo: 'MERCADOPAGO',   label: 'MercadoPago',   icon: Smartphone,     desc: 'Pago online con tarjeta / dinero en cuenta', habilitada: true  },
];

export default function Checkout() {
  const { items, getTotalPrice, clearCart } = useCartStore();
  const { isAuthenticated } = useAuthStore();
  const navigate = useNavigate();

  const [direcciones, setDirecciones] = useState<Direccion[]>([]);
  const [direccionId, setDireccionId] = useState<number | null>(null);
  const [formaPago,   setFormaPago]   = useState<FormaPagoCodigo>('MERCADOPAGO');
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [paso, setPaso] = useState<'creando' | 'pagando' | 'redirigiendo'>('creando');

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

  /**
   * FLUJO MERCADOPAGO:
   * 1) Crear pedido (estado PENDIENTE) en el backend
   * 2) Llamar a /pagos/crear → backend crea preference en MP
   * 3) Redirigir al init_point (Checkout PRO de MP)
   * 4) MP redirige a /pedido-exitoso/{id}?status=approved|pending|rejected
   * 5) MP notifica al webhook → backend avanza pedido a CONFIRMADO
   */
  const handleFinalizarPedido = async () => {
    if (!direccionId) {
      alert("Por favor, selecciona una dirección de entrega.");
      return;
    }

    try {
      setIsSubmitting(true);

      // ── Paso 1: crear pedido en estado PENDIENTE ──
      setPaso('creando');
      const itemsPayload = items.map(it => ({
        producto_id: it.producto.id,
        cantidad: it.cantidad,
      }));
      const pedidoCreado = await PedidoService.crear({
        direccion_id:      direccionId,
        forma_pago_codigo: formaPago,
        detalles:          itemsPayload,
      });

      // Si NO es MercadoPago (futuro), solo confirmamos
      if (formaPago !== 'MERCADOPAGO') {
        clearCart();
        navigate(`/pedido-exitoso/${pedidoCreado.id}?status=pending`);
        return;
      }

      // ── Paso 2: crear preference de pago en MP ──
      setPaso('pagando');
      const pago = await PagosService.crear(pedidoCreado.id);

      // ── Paso 3: redirigir al checkout de MP ──
      if (pago.init_point) {
        setPaso('redirigiendo');
        // Limpiamos carrito antes de salir
        clearCart();
        // Redirección a MercadoPago
        window.location.href = pago.init_point;
      } else {
        // Sin init_point: probablemente faltan credenciales TEST
        alert(
          "No se pudo obtener el link de pago de MercadoPago.\n" +
          "Verificá que MP_ACCESS_TOKEN esté configurado en el backend.\n\n" +
          "Tu pedido #" + pedidoCreado.id + " fue creado en estado PENDIENTE."
        );
        navigate(`/pedido-exitoso/${pedidoCreado.id}?status=pending`);
      }
    } catch (error: any) {
      console.error("Error al procesar el pedido", error);
      const status = error?.response?.status;
      const detail = error?.response?.data?.detail;
      let msg = "Hubo un error al procesar tu pedido.";
      if (status === 400) {
        msg = `Datos inválidos: ${detail || 'verificá los productos y la dirección'}`;
      } else if (status === 401) {
        msg = "Tu sesión expiró. Volvé a iniciar sesión.";
      } else if (status === 404) {
        msg = `No se encontró el recurso: ${detail || ''}`;
      } else if (status === 500) {
        msg = `Error del servidor: ${detail || 'revisá los logs del backend'}`;
      } else if (detail) {
        msg = `Error: ${detail}`;
      }
      alert(`${msg}\n\nDetalle técnico: ${JSON.stringify(error?.response?.data || error?.message)}`);
    } finally {
      setIsSubmitting(false);
      setPaso('creando');
    }
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <Loader2 className="w-10 h-10 animate-spin text-orange-600" />
    </div>
  );

  const botonLabel =
    paso === 'redirigiendo' ? (<><ExternalLink className="w-5 h-5" /> Redirigiendo a MercadoPago…</>) :
    paso === 'pagando'      ? (<><Loader2 className="w-5 h-5 animate-spin" /> Generando link de pago…</>) :
    paso === 'creando' && isSubmitting ? (<><Loader2 className="w-5 h-5 animate-spin" /> Creando pedido…</>) :
    (<><CreditCard className="w-5 h-5" /> CONFIRMAR Y PAGAR</>);

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4">
      <div className="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">

        {/* COLUMNA IZQUIERDA */}
        <div className="lg:col-span-2 space-y-6">
          <Link to="/" className="flex items-center gap-2 text-slate-500 hover:text-orange-600 transition-colors mb-4">
            <ArrowLeft className="w-4 h-4" /> Volver al catálogo
          </Link>

          <h1 className="text-3xl font-black text-slate-800">Finalizar Pedido</h1>

          {/* Dirección */}
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
                        <Check className="w-4 h-4" />
                      </div>
                    )}
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Método de Pago */}
          <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
            <div className="flex items-center gap-3 mb-6">
              <div className="bg-orange-100 p-2 rounded-xl text-orange-600">
                <CreditCard className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-bold text-slate-800">Método de Pago</h2>
              <span className="ml-auto text-[10px] font-black uppercase tracking-wider bg-blue-100 text-blue-600 px-2 py-1 rounded-full flex items-center gap-1">
                <Smartphone className="w-3 h-3" /> MERCADO PAGO
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {FORMAS_PAGO.map((fp) => {
                const Icon   = fp.icon;
                const active = formaPago === fp.codigo;
                const disabled = !fp.habilitada;
                return (
                  <label
                    key={fp.codigo}
                    className={`relative flex flex-col items-start gap-1.5 p-4 rounded-2xl border-2 transition-all ${
                      disabled
                        ? 'border-slate-100 bg-slate-50 opacity-60 grayscale cursor-not-allowed'
                        : active
                          ? 'border-blue-500 bg-blue-50/40 shadow-sm cursor-pointer'
                          : 'border-slate-100 hover:border-slate-200 cursor-pointer'
                    }`}
                  >
                    <input
                      type="radio"
                      name="formaPago"
                      className="hidden"
                      onChange={() => !disabled && setFormaPago(fp.codigo)}
                      checked={active}
                      disabled={disabled}
                    />
                    <div className="flex items-center gap-2">
                      <div className={`p-1.5 rounded-lg ${active ? 'bg-blue-500 text-white' : 'bg-slate-100 text-slate-500'}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <span className="font-bold text-slate-800 text-sm">{fp.label}</span>
                    </div>
                    <p className="text-xs text-slate-500 leading-snug">{fp.desc}</p>
                    {!disabled && active && (
                      <Check className="absolute top-2 right-2 w-4 h-4 text-blue-500" />
                    )}
                    {disabled && (
                      <span className="absolute top-2 left-2 inline-flex items-center gap-1 bg-slate-200 text-slate-600 text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full">
                        <Clock className="w-2.5 h-2.5" />
                        Próximamente
                      </span>
                    )}
                  </label>
                );
              })}
            </div>

            <div className="mt-4 p-4 bg-blue-50 border border-blue-100 rounded-xl flex gap-3">
              <Smartphone className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-blue-900 font-bold">Pago 100% seguro con MercadoPago</p>
                <p className="text-xs text-blue-700 mt-0.5">
                  Al confirmar, serás redirigido a MercadoPago para completar el pago con tarjeta de
                  crédito/débito, dinero en cuenta o Rapipago. Tu pedido se confirmará automáticamente.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* COLUMNA DERECHA: Resumen */}
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
                <span className="text-2xl font-black text-blue-600">${getTotalPrice()}</span>
              </div>
            </div>

            <button
              onClick={handleFinalizarPedido}
              disabled={isSubmitting || !direccionId}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white py-4 rounded-2xl font-black text-lg mt-8 transition-all shadow-lg active:scale-95 flex justify-center items-center gap-2"
            >
              {botonLabel}
            </button>

            <p className="text-[10px] text-slate-400 text-center mt-3">
              Al confirmar aceptás los términos de servicio de MercadoPago.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
