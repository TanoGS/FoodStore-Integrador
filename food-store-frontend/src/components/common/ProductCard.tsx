import { ShoppingCart } from 'lucide-react';
import { type Producto } from '../../types/producto.type';

interface ProductCardProps {
  producto: Producto;
}

export default function ProductCard({ producto }: ProductCardProps) {
  // Manejo temporal si no hay imagen en la base de datos
  const imagenPorDefecto = 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=500&q=60';

  const sinStock = producto.stock_disponible <= 0;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-xl transition-all duration-300 flex flex-col h-full group">
      
      {/* Contenedor de la Imagen */}
      <div className="relative h-52 w-full overflow-hidden bg-gray-100">
        <img 
          src={producto.imagen_url || imagenPorDefecto} 
          alt={producto.nombre}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
        />
        
        {/* Overlay si no hay stock */}
        {sinStock && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center backdrop-blur-sm">
            <span className="bg-red-600 text-white font-bold px-4 py-1.5 rounded-full text-sm uppercase tracking-wide">
              Agotado
            </span>
          </div>
        )}
      </div>

      {/* Cuerpo de la Tarjeta */}
      <div className="p-5 flex flex-col flex-grow">
        <div className="flex justify-between items-start gap-2 mb-2">
          <h3 className="font-bold text-xl text-gray-900 leading-tight">
            {producto.nombre}
          </h3>
        </div>
        
        {/* line-clamp-2 recorta el texto a 2 líneas y pone "..." al final */}
        <p className="text-gray-500 text-sm flex-grow line-clamp-2 mb-4">
          {producto.descripcion || 'Sin descripción disponible.'}
        </p>
        
        {/* Footer de la tarjeta: Precio y Botón */}
        <div className="flex items-center justify-between mt-auto pt-4 border-t border-gray-50">
          <span className="text-orange-600 font-extrabold text-2xl">
            ${producto.precio_base.toLocaleString()}
          </span>
          
          <button 
            disabled={sinStock || !producto.activo}
            className="bg-orange-600 hover:bg-orange-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white p-3 rounded-xl transition-colors shadow-sm flex items-center justify-center active:scale-95"
            title={sinStock ? 'Sin stock' : 'Agregar al carrito'}
            onClick={() => console.log('Pronto conectaremos Zustand aquí')}
          >
            <ShoppingCart className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
}