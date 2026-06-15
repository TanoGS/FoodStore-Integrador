import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { useState } from 'react';
import { User, LogIn, LogOut, Settings, MapPin, ShoppingCart, ShoppingBag } from 'lucide-react';
import { useCartStore } from '../../store/cartStore';
import CartDrawer from '../layout/CartDrawer';

const Navbar = () => {
  const { user, isAuthenticated, logout } = useAuthStore();
  const navigate = useNavigate();
  const totalItems = useCartStore(state => state.getTotalItems());
  const [isCartOpen, setIsCartOpen] = useState(false);

  const handleLogout = () => { logout(); navigate('/'); };


  // Conjunto que ADMIN_ROLES en App.tsx (incluye Cajero y Cocina
  
  const canSeeAdminPanel = user?.roles?.some((rol: any) => 
    ['ADMIN', 'GESTOR_STOCK', 'GESTOR_PEDIDOS', 'CAJERO', 'COCINA'].includes(rol.codigo || rol.rol_codigo)
  );

  return (
    <>
    <nav className="bg-slate-900 text-white p-2 flex justify-between items-center shadow-lg sticky top-0 z-50">
      <Link to="/" className="text-2xl font-black tracking-tight hover:text-orange-500 transition-colors">
        FOOD<span className="text-orange-500">STORE</span>
      </Link>

      <div className="flex items-center gap-5">
        
        {isAuthenticated ? (
          <>
            {/* Mis Pedidos */}
            <Link
              to="/mis-pedidos"
              className="flex items-center gap-1.5 text-slate-300 hover:text-orange-400 transition-colors text-sm font-medium"
            >
              <ShoppingBag className="w-5 h-5" />
              <span className="hidden md:block">Mis Pedidos</span>
            </Link>

            {/* Mis Direcciones  */}
            <Link
              to="/mis-direcciones"
              className="flex items-center gap-1.5 text-slate-300 hover:text-orange-400 transition-colors text-sm font-medium"
            >
              <MapPin className="w-5 h-5" />
              <span className="hidden md:block">Mis Direcciones</span>
            </Link>

            {/* Mi Perfil */}
            <Link
              to="/mi-perfil"
              className="flex items-center gap-1.5 text-slate-300 hover:text-orange-400 transition-colors text-sm font-medium"
            >
              <User className="w-5 h-5" />
              <span className="hidden md:block">Mi Perfil</span>
            </Link>

            {/* Carrito  */}
           <button 
                onClick={() => setIsCartOpen(true)}
                className="relative text-slate-300 hover:text-orange-400 transition-colors flex items-center"
              >
                <ShoppingCart className="w-6 h-6" />
                {totalItems > 0 && (
                  <span className="absolute -top-2 -right-2 bg-red-500 text-white text-[10px] w-5 h-5 flex items-center justify-center rounded-full font-bold shadow-md">
                    {totalItems}
                  </span>
                )}
              </button>

            {/* DIVISOR VISUAL */}
            <div className="h-8 w-px bg-slate-700 hidden sm:block mx-1"></div>

            {/* BOTÓN RESTRINGIDO POR ROL  */}
            {canSeeAdminPanel && (
              <Link 
                to="/admin"  
                className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 px-3 py-1.5 rounded-md transition-colors text-sm font-medium"
                title="Panel de Gestión"
              >
                <Settings className="w-4 h-4 text-orange-500" />
                <span className="hidden md:block">Panel</span>
              </Link>
            )}

            {/* --- VISTA DEL USUARIO --- */}
            <div className="flex items-center gap-3 bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700">
              <div className="flex flex-col text-right hidden sm:flex">
                <span className="text-[10px] text-orange-400 font-bold uppercase tracking-wider">
                  {user?.roles?.map((r: any) => r.nombre).join(', ')}
                </span>
                <span className="text-sm font-medium leading-tight">
                  {user?.nombre || user?.email.split('@')[0]}
                </span>
              </div>
              <User className="w-5 h-5 text-slate-300" />
              
              <button 
                onClick={handleLogout}
                className="ml-1 p-1 text-slate-400 hover:text-red-400 transition-colors"
                title="Cerrar Sesión"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </>
        ) : (
          // --- VISTA CUANDO NO ESTÁ LOGUEADO ---
          <div className="flex items-center gap-4">
            <Link 
              to="/registro" 
              className="text-sm font-medium text-slate-300 hover:text-white transition-colors hidden sm:block"
            >
              Crear Cuenta
            </Link>
            <Link 
              to="/login" 
              className="flex items-center gap-2 bg-orange-600 hover:bg-orange-500 px-4 py-2 rounded-xl transition-colors font-medium text-sm shadow-sm"
            >
              <span>Iniciar Sesión</span>
              <LogIn className="w-4 h-4" />
            </Link>
          </div>
        )}
      </div>
    </nav>

    {/* panel del carrito  */}
      <CartDrawer isOpen={isCartOpen} onClose={() => setIsCartOpen(false)} />
    </>
  );
};

export default Navbar;