import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <div className="bg-gray-300 flex flex-col items-center justify-center min-h-[80vh] px-4">
      <div className="text-center max-w-3xl">
        <h1 className="text-5xl md:text-6xl font-extrabold text-gray-900 tracking-tight mb-6">
          La mejor comida, <span className="text-orange-600">directo a tu puerta</span>
        </h1>
        <p className="text-xl text-gray-600 mb-10">
          Explora nuestro catálogo de lomos, hamburguesas y bebidas. Haz tu pedido en segundos y disfruta sin salir de casa.
        </p>
        <Link 
          to="/catalogo" 
          className="bg-orange-600 hover:bg-orange-700 text-white font-bold py-4 px-8 rounded-full text-lg transition duration-300 shadow-lg hover:shadow-xl"
        >
          Ver Catálogo Completo
        </Link>
      </div>

      {/* Sección de características rápidas */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-20 max-w-5xl w-full">
        <div className="bg-white p-6 rounded-2xl shadow-sm text-center">
          <div className="text-4xl mb-4">🚀</div>
          <h3 className="text-lg font-bold text-gray-800">Envío Rápido</h3>
          <p className="text-gray-500 mt-2">Tu comida caliente en menos de 45 minutos.</p>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm text-center">
          <div className="text-4xl mb-4">💳</div>
          <h3 className="text-lg font-bold text-gray-800">Pago Seguro</h3>
          <p className="text-gray-500 mt-2">Integración total con MercadoPago.</p>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm text-center">
          <div className="text-4xl mb-4">🍔</div>
          <h3 className="text-lg font-bold text-gray-800">Calidad Premium</h3>
          <p className="text-gray-500 mt-2">Ingredientes frescos y de primera calidad.</p>
        </div>
      </div>
    </div>
  );
}