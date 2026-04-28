import { Link } from 'react-router-dom';
import { ShoppingCart, User, Menu } from 'lucide-react';

export default function Navbar() {
  return (
    <nav className="bg-white shadow-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          
          {/* Logo y enlaces principales */}
          <div className="flex items-center gap-8">
            <Link to="/" className="text-2xl font-bold text-orange-600">
              FoodStore
            </Link>
            <div className="hidden md:flex space-x-4">
              <Link to="/" className="text-gray-700 hover:text-orange-600 font-medium">Inicio</Link>
              <Link to="/catalogo" className="text-gray-700 hover:text-orange-600 font-medium">Catálogo</Link>
            </div>
          </div>

          {/* Íconos de usuario y carrito */}
          <div className="flex items-center space-x-6">
            <Link to="/login" className="text-gray-600 hover:text-orange-600">
              <User className="h-6 w-6" />
            </Link>
            
            <Link to="/carrito" className="text-gray-600 hover:text-orange-600 relative">
              <ShoppingCart className="h-6 w-6" />
              {/* Badge del carrito (hardcodeado por ahora) */}
              <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center">
                0
              </span>
            </Link>
            
            {/* Menú hamburguesa para móvil */}
            <button className="md:hidden text-gray-600">
              <Menu className="h-6 w-6" />
            </button>
          </div>

        </div>
      </div>
    </nav>
  );
}