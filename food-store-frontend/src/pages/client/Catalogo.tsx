import { useEffect, useState } from 'react';
import { CategoriaService, type CategoriaConProductos } from '../../services/categoria.service';
import ProductCard from '../../components/common/ProductCard';

export default function Catalogo() {
  const [categorias, setCategorias] = useState<CategoriaConProductos[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    CategoriaService.listarConProductos()
      .then(data => setCategorias(data))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-10">
      <header className="mb-12 text-center">
        <h1 className="text-4xl font-extrabold text-gray-900 mb-2">Nuestro Menú</h1>
        <p className="text-gray-500">Selecciona tus favoritos y arma tu pedido</p>
      </header>

      {/* RECORREMOS LAS CATEGORÍAS */}
      {categorias.map((cat) => (
        <section key={cat.id} className="mb-16">
          {/* Título de la Categoría */}
          <div className="flex items-center gap-4 mb-8">
            <h2 className="text-2xl font-bold text-gray-800 whitespace-nowrap">
              {cat.nombre}
            </h2>
            <div className="h-[2px] w-full bg-gray-100"></div> {/* Línea decorativa */}
          </div>

          {/* Grilla de Productos de ESTA categoría */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
            {cat.productos.map((prod) => (
              <ProductCard key={prod.id} producto={prod} />
            ))}
          </div>
        </section>
      ))}

      {categorias.length === 0 && (
        <div className="text-center py-20 text-gray-500">
          No hay productos disponibles en este momento.
        </div>
      )}
    </div>
  );
}