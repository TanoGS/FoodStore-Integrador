import { X, Plus, Minus, Trash2, ShoppingBag } from 'lucide-react';
import { useCartStore } from '../../store/cartStore';
import { Link, useNavigate } from 'react-router-dom';

interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CartDrawer({ isOpen, onClose }: CartDrawerProps) {
  // Traemos todo lo que necesitamos de nuestro store de Zustand
  const { items, updateQuantity, removeItem, getTotalPrice, clearCart } = useCartStore();
  const navigate = useNavigate();

  // Si no está abierto, no renderizamos el panel
  if (!isOpen) return null;

  const handleCheckout = () => {
    onClose();
    navigate('/checkout'); // O a la ruta de pago proxima
  };

  return (
    <>
      {/* Fondo oscuro (Overlay) */}
      <div 
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[60] transition-opacity"
        onClick={onClose}
      />

      {/* Panel lateral derecho */}
      <div className="fixed top-0 right-0 h-full w-full sm:w-96 bg-white shadow-2xl z-[70] flex flex-col transform transition-transform duration-300 ease-in-out overflow-hidden">
        
        {/* Cabecera del carrito */}
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
          <h2 className="text-xl font-black text-slate-800 flex items-center gap-2">
            <ShoppingBag className="text-orange-500 w-6 h-6" />
            Tu Pedido
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 bg-white p-2 rounded-full shadow-sm">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Lista de productos */}
        <div className="flex-1 overflow-y-auto p-6">
          {items.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-4">
              <ShoppingBag className="w-20 h-20 opacity-20" />
              <p className="text-lg font-medium">Tu carrito está vacío</p>
              <button onClick={onClose} className="text-orange-600 font-bold hover:underline">
                Ir al menú
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {items.map((item) => (
                <div key={item.producto.id} className="flex gap-4 items-center bg-white border border-slate-100 p-3 rounded-2xl shadow-sm">
                  {/* Foto del producto (si tiene) */}
                  <div className="w-20 h-20 bg-slate-100 rounded-xl flex-shrink-0 overflow-hidden">
                    <img 
                      src={item.producto.imagen_url || "https://via.placeholder.com/150"} 
                      alt={item.producto.nombre}
                      className="w-full h-full object-cover"
                    />
                  </div>

                  {/* Info del producto */}
                  <div className="flex-1">
                    <h3 className="font-bold text-slate-800 text-sm leading-tight mb-1">
                      {item.producto.nombre}
                    </h3>
                    <p className="text-orange-600 font-black text-sm">
                      ${item.producto.precio_base}
                    </p>

                    {/* Controles de cantidad */}
                    <div className="flex items-center gap-3 mt-2">
                      <div className="flex items-center bg-slate-100 rounded-lg p-1">
                        <button 
                          onClick={() => updateQuantity(item.producto.id, item.cantidad - 1)}
                          className="w-6 h-6 flex items-center justify-center bg-white rounded shadow-sm text-slate-600 hover:text-orange-600 transition-colors"
                        >
                          <Minus className="w-3 h-3" />
                        </button>
                        <span className="w-8 text-center text-sm font-bold text-slate-700">
                          {item.cantidad}
                        </span>
                        <button 
                          onClick={() => updateQuantity(item.producto.id, item.cantidad + 1)}
                          className="w-6 h-6 flex items-center justify-center bg-white rounded shadow-sm text-slate-600 hover:text-orange-600 transition-colors"
                        >
                          <Plus className="w-3 h-3" />
                        </button>
                      </div>
                      <button 
                        onClick={() => removeItem(item.producto.id)}
                        className="text-slate-400 hover:text-red-500 p-1 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer del carrito (Totales y Botón de Pago) */}
        {items.length > 0 && (
          <div className="p-6 bg-white border-t border-slate-100 shadow-[0_-10px_40px_-15px_rgba(0,0,0,0.1)]">
            <div className="flex justify-between items-center mb-4">
              <span className="text-slate-500 font-medium">Total a pagar:</span>
              <span className="text-2xl font-black text-slate-800">
                ${getTotalPrice()}
              </span>
            </div>
            
            <button 
              onClick={handleCheckout}
              className="w-full bg-orange-600 hover:bg-orange-700 text-white py-4 rounded-xl font-bold text-lg shadow-lg shadow-orange-600/30 transition-transform active:scale-95"
            >
              Confirmar Pedido
            </button>
            
            <button 
              onClick={clearCart}
              className="w-full text-center mt-4 text-sm font-medium text-slate-400 hover:text-slate-600"
            >
              Vaciar carrito
            </button>
          </div>
        )}

      </div>
    </>
  );
}