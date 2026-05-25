import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { Package, Tags, Carrot, LogOut, LayoutDashboard, Users, ClipboardList } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { useEffect } from 'react';

export default function AdminLayout() {
  const { user, isAuthenticated, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (!isAuthenticated) return null;

  // Definimos qué roles pueden ver cada ítem del menú
  const navItems = [
    { 
      name: 'Dashboard', 
      path: '/admin', 
      icon: LayoutDashboard, 
      roles: ['ADMIN', 'GESTOR_STOCK', 'GESTOR_PEDIDOS'] 
    },
    { 
      name: 'Productos', 
      path: '/admin/productos', 
      icon: Package, 
      roles: ['ADMIN', 'GESTOR_STOCK'] 
    },
    { 
      name: 'Categorías', 
      path: '/admin/categorias', 
      icon: Tags, 
      roles: ['ADMIN', 'GESTOR_STOCK'] 
    },
    { 
      name: 'Ingredientes', 
      path: '/admin/ingredientes', 
      icon: Carrot, 
      roles: ['ADMIN', 'GESTOR_STOCK'] 
    },
    { 
      name: 'Pedidos', 
      path: '/admin/pedidos', 
      icon: ClipboardList, 
      roles: ['ADMIN', 'GESTOR_PEDIDOS'] 
    },
    { 
      name: 'Usuarios', 
      path: '/admin/usuarios', 
      icon: Users, 
      roles: ['ADMIN'] 
    }
  ];

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden">
      {/* Sidebar / Menú Lateral */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col z-20 shadow-xl">
        
        {/* Logo de la Empresa */}
        <div className="p-6 border-b border-slate-800 bg-slate-950 flex items-center justify-between">
          <Link to="/" className="text-xl font-black tracking-tight hover:text-orange-500 transition-colors">
            FOOD<span className="text-orange-500">STORE</span>
          </Link>
          <span className="text-[10px] bg-slate-800 border border-slate-700 px-2 py-0.5 rounded text-orange-400 font-bold uppercase">
            Panel
          </span>
        </div>

        {/* 🔐 NAVEGACIÓN FILTRADA POR ROLES (RBAC CORPORATIVO) */}
        <nav className="flex-1 p-4 space-y-1.5 overflow-y-auto">
          {navItems
            .filter(item => 
              // Comparamos los códigos de los roles del usuario contra los permitidos por el botón
              user?.roles?.some((uRol: any) => item.roles.includes(uRol.codigo || uRol.rol_codigo))
            )
            .map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                    isActive 
                      ? 'bg-orange-600 text-white shadow-lg shadow-orange-600/20' 
                      : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span className="font-medium">{item.name}</span>
                </Link>
              );
            })}
        </nav>

        {/* Perfil del Empleado y Cerrar Sesión */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/50">
          <div className="flex items-center justify-between gap-2">
            <div className="overflow-hidden flex-1">
              <p className="text-sm font-bold truncate">{user?.nombre || 'Usuario'}</p>
              <p className="text-[10px] text-orange-400 font-bold uppercase tracking-wider truncate">
                {user?.roles?.map((r: any) => r.nombre.replace('_', ' ')).join(', ')}
              </p>
            </div>
            <button 
              onClick={handleLogout} 
              className="text-slate-500 hover:text-red-500 p-2 transition-colors shrink-0"
              title="Cerrar Sesión"
            >
              <LogOut className="h-5 w-5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Área de Contenido de cada Módulo (Tablas, Modales, etc) */}
      <main className="flex-1 overflow-y-auto p-8 relative">
        <Outlet />
      </main>
    </div>
  );
}