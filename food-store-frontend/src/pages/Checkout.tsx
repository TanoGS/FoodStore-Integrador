import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useCartStore } from '../store/cartStore';
import { useAuthStore } from '../store/authStore';
import { DireccionService, type Direccion } from '../services/direccion.service';
import { PedidoService } from '../services/pedido.service';
import { PagosService } from '../services/pagos.service';
import {
  MapPin, ShoppingBag, CreditCard, ArrowLeft, Loader2, Plus,
  Banknote, Smartphone, Check, Clock, ExternalLink, Store, Truck,
  AlertCircle, XCircle, CheckCircle2,
} from 'lucide-react';

type FormaPagoCodigo = 'EFECTIVO' | 'MERCADOPAGO';
export type TipoEntrega = 'EN_LOCAL' | 'DELIVERY';

interface FormaPagoItem {
  codigo: FormaPagoCodigo;
  label: string;
  icon: React.ElementType;
  desc: string;
}

const FORMAS_PAGO: FormaPagoItem[] = [
  {
    codigo: 'EFECTIVO',
    label: 'Efectivo',
    icon: Banknote,
    desc: 'Pagás al confirmar el pedido',
  },
  {
    codigo: 'MERCADOPAGO',
    label: 'MercadoPago',
    icon: Smartphone,
    desc: 'Pago online con tarjeta / dinero en cuenta',
  },
];

const TIPO_ENTREGA_ITEMS: { codigo: TipoEntrega; label: string; icon: React.ElementType; desc: string }[] = [
  { codigo: 'EN_LOCAL', label: 'En el local', icon: Store, desc: 'Venís a retirar tu pedido al local' },
  { codigo: 'DELIVERY', label: 'Delivery',    icon: Truck,  desc: 'Te lo llevamos a tu dirección'     },
];

export default function Checkout() {
  const { items, getTotalPrice, clearCart } = useCartStore();
  const { isAuthenticated } = useAuthStore();
  const navigate = useNavigate();

  const [direcciones, setDirecciones] = useState<Direccion[]>([]);
  const [direccionId, setDireccionId] = useState<number | null>(null);
  const [tipoEntrega, setTipoEntrega] = useState<TipoEntrega>('DELIVERY');
  const [formaPago,   setFormaPago]   = useState<FormaPagoCodigo>('MERCADOPAGO');
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [paso, setPaso] = useState<'creando' | 'pagando' | 'redirigiendo'>('creando');
  const [toast, setToast] = useState<{ tipo: 'ok' | 'err'; msg: string } | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Redirect if not authenticated or cart empty
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login?redirect=checkout');
      return;
    }
    if (items.length === 0) {
      navigate('/');
      return;
    }
  }, [isAuthenticated, items.length, navigate]);

  // Load direcciones and set defaults
  useEffect(() => {
    const cargarDatos = async () => {
      try {
        const data = await DireccionService.listar();
        setDirecciones(data);
        if (tipoEntrega === 'DELIVERY') {
          const principal = data.find((d: Direccion) => d.predeterminada);
          if (principal) setDireccionId(principal.id);
          else if (data.length > 0) setDireccionId(data[0].id);
        }
      } catch (error) {
        console.error("Error al cargar direcciones", error);
      } finally {
        setLoading(false);
      }
    };
    cargarDatos();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // When tipoEntrega changes to DELIVERY, select a default address
  useEffect(() => {
    if (tipoEntrega === 'DELIVERY' && direcciones.length > 0 && !direccionId) {
      const principal = direcciones.find((d: Direccion) => d.predeterminada);
      if (principal) setDireccionId(principal.id);
      else setDireccionId(direcciones[0].id);
    }
  }, [tipoEntrega, direcciones, direccionId]);

  // Si cambia a DELIVERY y está seleccionado EFECTIVO, forzar a MERCADOPAGO
  // (EFECTIVO no está disponible para delivery)
  useEffect(() => {
    if (tipoEntrega === 'DELIVERY' && formaPago === 'EFECTIVO') {
      setFormaPago('MERCADOPAGO');
    }
  }, [tipoEntrega]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-dismiss del toast
  useEffect(() => {
    if (!toast) return;
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 4000);
    return () => { if (toastTimer.current) clearTimeout(toastTimer.current); };
  }, [toast]);

  const handleFinalizarPedido = async () => {
    if (tipoEntrega === 'DELIVERY' && !direccionId) {
      alert("Por favor, seleccioná una dirección de entrega.");
      return;
    }

    try {
      setIsSubmitting(true);
      setPaso('creando');

      const itemsPayload = items.map(it => ({
        producto_id: it.producto.id,
        cantidad: it.cantidad,
        personalizacion: it.producto.personalizacion
          ? it.producto.personalizacion.map(p => p.id)
          : null,
      }));

      const pedidoCreado = await PedidoService.crear({
        direccion_id:       tipoEntrega === 'DELIVERY' ? direccionId : null,
        forma_pago_codigo:  formaPago,
        tipo_entrega:        tipoEntrega,
        detalles:            itemsPayload,
      });

      // EFECTIVO → pantalla de confirmación sin redirigir a MP
      if (formaPago !== 'MERCADOPAGO') {
        clearCart();
        navigate(`/pedido-exitoso/${pedidoCreado.id}?status=pending&forma_pago=${formaPago}`);
        return;
      }

      // MERCADOPAGO → redirigir a MP
      setPaso('pagando');
      const pago = await PagosService.crear(pedidoCreado.id);

      if (pago.init_point) {
        setPaso('redirigiendo');
        clearCart();
        window.location.href = pago.init_point;
      } else {
        alert(
          "No se pudo obtener el link de pago de MercadoPago.\n" +
          "Verificá que MP_ACCESS_TOKEN esté configurado en el backend.\n\n" +
          "Tu pedido #" + pedidoCreado.id + " fue creado en estado PENDIENTE."
        );
        navigate(`/pedido-exitoso/${pedidoCreado.id}?status=pending`);
      }
    } catch (error: any) {
      console.error("Error al procesar el pedido", error?.response?.data || error);
      const status = error?.response?.status;
      const detail = error?.response?.data?.detail;

      // Caso especial: stock insuficiente → mensaje genérico (no filtrar detalles)
      const esStockInsuficiente =
        status === 400 &&
        typeof detail === 'object' &&
        detail?.error === 'stock_insuficiente';

      let msg = "Hubo un error al procesar tu pedido.";

      if (esStockInsuficiente) {
        msg = "En este momento no podemos realizar tu pedido. Por favor, intentá más tarde o contactanos.";
      } else if (status === 400) {
        msg = typeof detail === 'string'
          ? `Datos inválidos: ${detail}`
          : "Datos inválidos: verificá los productos y la dirección";
      } else if (status === 401) {
        msg = "Tu sesión expiró. Volvé a iniciar sesión.";
      } else if (status === 404) {
        msg = `No se encontró el recurso: ${typeof detail === 'string' ? detail : ''}`;
      } else if (status === 500) {
        msg = "Error del servidor. Por favor, intentá más tarde.";
      } else {
        msg = typeof detail === 'string' ? detail : "Ocurrió un error inesperado.";
      }

      setToast({ tipo: 'err', msg });
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

  const shippingCost = tipoEntrega === 'DELIVERY' ? 50 : 0;
  const totalPrice = getTotalPrice();
  const finalTotal = totalPrice + shippingCost;
  const requiresDireccion = tipoEntrega === 'DELIVERY' && !direccionId;

  const botonLabel =
    paso === 'redirigiendo' ? (<><ExternalLink className="w-5 h-5" /> Redirigiendo a MercadoPago…</>) :
    paso === 'pagando'      ? (<><Loader2 className="w-5 h-5 animate-spin" /> Generando link de pago…</>) :
    paso === 'creando' && isSubmitting ? (<><Loader2 className="w-5 h-5 animate-spin" /> Creando pedido…</>) :
    formaPago === 'EFECTIVO'
      ? (<><Banknote className="w-5 h-5" /> CONFIRMAR PEDIDO</>)
      : (<><CreditCard className="w-5 h-5" /> CONFIRMAR Y PAGAR</>);

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4">

      {/* ── Toast de feedback ─────────────────────────────────────────── */}
      {toast && (
        <div
          className={`mb-6 flex items-center gap-3 px-5 py-3 rounded-xl border-2 text-sm font-bold ${
            toast.tipo === 'ok'
              ? 'bg-green-50 border-green-200 text-green-800'
              : 'bg-red-50 border-red-200 text-red-800'
          }`}
        >
          {toast.tipo === 'ok'
            ? <CheckCircle2 className="w-5 h-5 shrink-0" />
            : <XCircle className="w-5 h-5 shrink-0" />}
          <span className="flex-1">{toast.msg}</span>
          <button
            onClick={() => { setToast(null); if (toastTimer.current) clearTimeout(toastTimer.current); }}
            className="ml-2 hover:opacity-70 transition-opacity"
          >
            <XCircle className="w-4 h-4" />
          </button>
        </div>
      )}

      <div className="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">

        {/* ── COLUMNA IZQUIERDA ── */}
        <div className="lg:col-span-2 space-y-6">
          <Link to="/" className="flex items-center gap-2 text-slate-500 hover:text-orange-600 transition-colors mb-4">
            <ArrowLeft className="w-4 h-4" /> Volver al catálogo
          </Link>

          <h1 className="text-3xl font-black text-slate-800">Finalizar Pedido</h1>

          {/* ── Tipo de Entrega ── */}
          <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
            <div className="flex items-center gap-3 mb-6">
              <div className="bg-orange-100 p-2 rounded-xl text-orange-600">
                <Store className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-bold text-slate-800">Tipo de Entrega</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {TIPO_ENTREGA_ITEMS.map((te) => {
                const Icon = te.icon;
                const active = tipoEntrega === te.codigo;
                return (
                  <label
                    key={te.codigo}
                    className={`relative flex flex-col items-start gap-1.5 p-4 rounded-2xl border-2 cursor-pointer transition-all ${
                      active
                        ? 'border-orange-500 bg-orange-50/40 shadow-sm'
                        : 'border-slate-100 hover:border-slate-200'
                    }`}
                  >
                    <input
                      type="radio"
                      name="tipoEntrega"
                      className="hidden"
                      onChange={() => {
                        setTipoEntrega(te.codigo);
                        if (te.codigo === 'EN_LOCAL') {
                          // En local: no necesita dirección
                          setDireccionId(null);
                        }
                      }}
                      checked={active}
                    />
                    <div className="flex items-center gap-2">
                      <div className={`p-1.5 rounded-lg ${active ? 'bg-orange-500 text-white' : 'bg-slate-100 text-slate-500'}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <span className="font-bold text-slate-800 text-sm">{te.label}</span>
                    </div>
                    <p className="text-xs text-slate-500 leading-snug">{te.desc}</p>
                    {active && (
                      <Check className="absolute top-2 right-2 w-4 h-4 text-orange-500" />
                    )}
                  </label>
                );
              })}
            </div>
          </div>

          {/* ── Dirección (solo si es delivery) ── */}
          {tipoEntrega === 'DELIVERY' && (
            <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
              <div className="flex items-center gap-3 mb-6">
                <div className="bg-orange-100 p-2 rounded-xl text-orange-600">
                  <MapPin className="w-6 h-6" />
                </div>
                <h2 className="text-xl font-bold text-slate-800">Dirección de Entrega</h2>
              </div>

              {direcciones.length === 0 ? (
                <div className="text-center py-6 border-2 border-dashed border-slate-200 rounded-2xl">
                  <p className="text-slate-500 mb-4">No tenés direcciones registradas</p>
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
                        direccionId === dir.id
                          ? 'border-orange-500 bg-orange-50/30'
                          : 'border-slate-100 hover:border-slate-200'
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
          )}

          {/* ── Método de Pago ── */}
          <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
            <div className="flex items-center gap-3 mb-6">
              <div className="bg-orange-100 p-2 rounded-xl text-orange-600">
                <CreditCard className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-bold text-slate-800">Método de Pago</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {FORMAS_PAGO.map((fp) => {
                const Icon = fp.icon;
                const active = formaPago === fp.codigo;
                // EFECTIVO no está disponible para delivery
                const isDisabled = tipoEntrega === 'DELIVERY' && fp.codigo === 'EFECTIVO';
                return (
                  <label
                    key={fp.codigo}
                    className={`relative flex flex-col items-start gap-1.5 p-4 rounded-2xl border-2 transition-all ${
                      isDisabled
                        ? 'border-slate-100 bg-slate-50 opacity-60 cursor-not-allowed'
                        : active
                          ? 'border-blue-500 bg-blue-50/40 shadow-sm cursor-pointer'
                          : 'border-slate-100 hover:border-slate-200 cursor-pointer'
                    }`}
                  >
                    <input
                      type="radio"
                      name="formaPago"
                      className="hidden"
                      onChange={() => !isDisabled && setFormaPago(fp.codigo)}
                      checked={active}
                      disabled={isDisabled}
                    />
                    <div className="flex items-center gap-2">
                      <div className={`p-1.5 rounded-lg ${active ? 'bg-blue-500 text-white' : 'bg-slate-100 text-slate-500'}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <span className="font-bold text-slate-800 text-sm">{fp.label}</span>
                    </div>
                    <p className="text-xs text-slate-500 leading-snug">{fp.desc}</p>
                    {isDisabled && (
                      <span className="absolute top-2 right-2 text-[9px] font-bold text-slate-400 uppercase tracking-wider">
                        No disponible
                      </span>
                    )}
                    {active && !isDisabled && (
                      <Check className="absolute top-2 right-2 w-4 h-4 text-blue-500" />
                    )}
                    {fp.codigo === 'MERCADOPAGO' && !isDisabled && (
                      <span className="absolute top-2 left-2 inline-flex items-center gap-1 bg-blue-100 text-blue-700 text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full">
                        <Smartphone className="w-2.5 h-2.5" />
                        Recomendado
                      </span>
                    )}
                  </label>
                );
              })}
            </div>

            {formaPago === 'EFECTIVO' && (
              <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-xl flex gap-3">
                <Banknote className="w-5 h-5 text-yellow-600 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-yellow-900 font-bold">Pagás al confirmar el pedido</p>
                  <p className="text-xs text-yellow-700 mt-0.5">
                    Un cajero verificará tu pedido y te indicará el monto a pagar. Tu pedido queda en
                    espera hasta que el pago sea confirmado.
                  </p>
                </div>
              </div>
            )}
            {formaPago === 'MERCADOPAGO' && (
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
            )}
          </div>
        </div>

        {/* ── COLUMNA DERECHA: Resumen ── */}
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
                <span>${totalPrice}</span>
              </div>
              <div className="flex justify-between items-center text-slate-500">
                <span>Envío</span>
                {shippingCost === 0 ? (
                  <span className="text-green-600 font-bold">¡Gratis!</span>
                ) : (
                  <span>${shippingCost}</span>
                )}
              </div>
              <div className="flex justify-between items-center pt-2">
                <span className="text-xl font-black text-slate-800">Total</span>
                <span className="text-2xl font-black text-blue-600">${finalTotal.toFixed(1)}</span>
              </div>
            </div>

            <button
              onClick={handleFinalizarPedido}
              disabled={isSubmitting || requiresDireccion}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white py-4 rounded-2xl font-black text-lg mt-8 transition-all shadow-lg active:scale-95 flex justify-center items-center gap-2"
              title={requiresDireccion ? 'Seleccioná una dirección de entrega para continuar' : undefined}
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
