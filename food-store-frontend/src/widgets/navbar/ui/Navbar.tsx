import { Link } from 'react-router-dom';
import { useAuthStore } from '../../../store/authStore';
import { useCartStore } from '../../../store/cartStore';

export const Navbar = () => {
  // 1. Extraemos 'user' además de isAuthenticated y logout
  const { isAuthenticated, logout, user } = useAuthStore();
  const cartItems = useCartStore((state) => state.items);

  return (
    <nav className="bg-white shadow-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo / Título */}
          <Link to="/" className="flex items-center">
            <span className="text-2xl font-bold text-orange-600">🍔 Food Store</span>
          </Link>

          {/* Menú de navegación */}
          <div className="flex items-center space-x-4">
            {/* Botón del Carrito */}
            <button className="relative p-2 text-gray-600 hover:text-orange-600 transition-colors">
              <svg className="w-6 h-6" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24" stroke="currentColor">
                <path d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"></path>
              </svg>
              {cartItems.length > 0 && (
                <span className="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white transform translate-x-1/4 -translate-y-1/4 bg-red-600 rounded-full">
                  {cartItems.length}
                </span>
              )}
            </button>

            {/* Lógica de Autenticación */}
            {isAuthenticated ? (
              <div className="flex items-center space-x-4">

                {/* 2. Mostramos el email del usuario (oculto en pantallas muy pequeñas por diseño) */}
                {user && (
                  <span className="text-sm font-medium text-gray-500 hidden sm:block">
                    {user.email}
                  </span>
                )}
              
                {user?.rol_nombre === 'ADMIN' && (
                  <Link to="/admin" className="text-gray-600 hover:text-orange-600 font-medium transition-colors text-sm">
                    Panel Admin
                  </Link>
                )}

                <button
                  onClick={logout}
                  className="bg-gray-200 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-300 transition-colors text-sm font-bold"
                >
                  Salir
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                className="bg-orange-600 text-white px-4 py-2 rounded-md hover:bg-orange-700 transition-colors text-sm font-bold"
              >
                Iniciar Sesión
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};