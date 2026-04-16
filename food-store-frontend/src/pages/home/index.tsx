import { Navbar } from '../../widgets/navbar/ui/Navbar';
import { ProductoCard } from '../../entities/producto/ui/ProductoCard';

// Mocks temporales para ver la estructura
const MOCK_PRODUCTOS = [
  { id: 1, nombre: "Hamburguesa Clásica", descripcion: "Medallón de carne 200g, queso cheddar, lechuga, tomate y salsa especial.", precio: 8500 },
  { id: 2, nombre: "Papas Cheddar", descripcion: "Porción de papas fritas rústicas bañadas en queso cheddar y panceta crujiente.", precio: 4500 },
  { id: 3, nombre: "Pizza Margherita", descripcion: "Masa madre, salsa de tomate natural, mozzarella fior di latte y albahaca fresca.", precio: 12000 },
  { id: 4, nombre: "Ensalada Caesar", descripcion: "Mix de hojas verdes, croutons, queso parmesano, pollo grillado y aderezo caesar.", precio: 7000 },
];

export const HomePage = () => {
  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      <Navbar />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="mb-8">
          <h1 className="text-4xl font-extrabold text-gray-900 mb-2">Nuestro Menú</h1>
          <p className="text-lg text-gray-600">Descubre nuestros deliciosos platos preparados en el momento.</p>
        </div>

        {/* Grilla responsiva para los productos */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {MOCK_PRODUCTOS.map((producto) => (
            <ProductoCard 
              key={producto.id}
              id={producto.id}
              nombre={producto.nombre}
              descripcion={producto.descripcion}
              precio={producto.precio}
            />
          ))}
        </div>
      </main>
    </div>
  );
};