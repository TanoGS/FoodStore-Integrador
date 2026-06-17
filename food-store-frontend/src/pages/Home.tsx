import { useState, useEffect } from 'react';
import { ShoppingBag, Utensils } from 'lucide-react';
import { CatalogoService } from '../services/catalogo.service';
import { useCartStore } from '../store/cartStore';
import { useAuthStore } from '../store/authStore';
import PersonalizarModal from '../components/client/PersonalizarModal';
import type { Producto } from '../types/producto.type';

interface Categoria {
  id: number;
  nombre: string;
  productos?: Producto[];
}

export default function Home() {
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [loading, setLoading] = useState(true);
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);

  // Modal de personalización
  const [productoPersonalizar, setProductoPersonalizar] = useState<Producto | null>(null);

  useEffect(() => {
    const fetchMenu = async () => {
      try {
        // Traer productos con receta_detallada para ver alérgenos y removibles
        const [cats, prods] = await Promise.all([
          CatalogoService.getCategorias(),
          CatalogoService.getProductos(),
        ]);

        // Agrupamos los productos activos dentro de sus respectivas categorías
        const menuAgrupado = cats.map((cat: any) => {
          return {
            ...cat,
            productos: prods.filter((p: Producto) =>
              p.activo && p.categorias?.some((c: any) => c.id === cat.id)
            )
          };
        }).filter((cat: Categoria) => cat.productos && cat.productos.length > 0);

        setCategorias(menuAgrupado);
      } catch (error) {
        console.error("Error al cargar el menú:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchMenu();
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">

      {/* HERO SECTION */}
      <div className="bg-slate-900 text-white py-8 px-3">
        <div className="max-w-2xl mx-auto text-center">
          <h1 className="text-4xl md:text-5xl font-black mb-4 tracking-tight">
            El sabor que te <span className="text-orange-500">apasiona</span>,<br/>
            directo a tu puerta.
          </h1>
          <p className="text-lg text-slate-200 max-w-2xl mx-auto mb-1">
            Descubre nuestro menú renovado con los mejores ingredientes y calidad premium.
          </p>
        </div>
      </div>

      {/* MENÚ SECTION */}
      <div className="max-w-7xl mx-auto px-4 py-16">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mb-4"></div>
            <p className="text-slate-500 font-medium">Preparando la cocina...</p>
          </div>
        ) : categorias.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-3xl border border-slate-100 shadow-sm">
            <ShoppingBag className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-slate-700">El menú está vacío</h3>
            <p className="text-slate-500">Aún no hay productos disponibles para mostrar.</p>
          </div>
        ) : (
          <div className="space-y-16">
            {categorias.map((cat) => (
              <section key={cat.id}>
                <h2 className="text-2xl font-black text-slate-800 mb-6 flex items-center gap-2">
                  <Utensils className="w-6 h-6 text-orange-600" />
                  {cat.nombre}
                </h2>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {cat.productos?.map((producto) => (
                    <div key={producto.id} className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden hover:shadow-lg transition-all group flex flex-col">

                      <div className="relative h-48 bg-slate-100 overflow-hidden">
                        <img
                          src={producto.imagenes_url?.[0] ?? producto.imagen_url ?? 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=800&q=80'}
                          alt={producto.nombre}
                          className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                          onError={(e) => {
                            const target = e.currentTarget;
                            if (!target.dataset.fallbackUsed) {
                              target.dataset.fallbackUsed = 'true';
                              target.src = 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=800&q=80';
                            }
                          }}
                        />
                        <div className="absolute top-4 right-4 bg-white/90 backdrop-blur px-3 py-1 rounded-full font-black text-slate-900 shadow-sm">
                          ${producto.precio}
                        </div>
                        {/* Indicador de personalización */}
                        {(producto.receta_detallada?.length ?? 0) > 0 && (
                          <div className="absolute top-4 left-4 bg-orange-500/90 backdrop-blur px-2 py-1 rounded-full">
                            <span className="text-white text-xs font-bold">Personalizable</span>
                          </div>
                        )}
                      </div>

                      <div className="p-6 flex-1 flex flex-col">
                        <h3 className="text-xl font-bold text-slate-800 mb-2">{producto.nombre}</h3>
                        <p className="text-slate-500 text-sm line-clamp-2 mb-6 flex-1">
                          {producto.descripcion || "Ingredientes frescos y sabor inigualable."}
                        </p>
                        {isAuthenticated && (
                          <button
                            onClick={() => setProductoPersonalizar(producto)}
                            className="w-full bg-slate-900 hover:bg-orange-600 text-white font-bold py-3 rounded-2xl transition-all flex items-center justify-center gap-2 active:scale-95 shadow-lg shadow-slate-200"
                          >
                            Agregar
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>

      {/* Modal de personalización */}
      {productoPersonalizar && (
        <PersonalizarModal
          producto={productoPersonalizar}
          onClose={() => setProductoPersonalizar(null)}
        />
      )}
    </div>
  );
}
