import { useState, useEffect } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { 
  Package, Tags, Carrot, LogOut, LayoutDashboard, Users, 
  ClipboardList, ChefHat, Banknote, ChevronLeft, ChevronRight,
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';

const SIDEBAR_KEY = 'admin-sidebar-collapsed';

export default function AdminLayout() {
  const { user, isAuthenticated, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  // Estado de colapso: se inicializa desde sessionStorage para que
  // sobreviva al refresh de la misma tab.
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return sessionStorage.getItem(SIDEBAR_KEY) === 'true';
    } catch {
      return false;
    }
  });

  // Toggle con persistencia
  const toggleSidebar = () => {
    const next = !collapsed;
    setCollapsed(next);
    try {
      sessionStorage.setItem(SIDEBAR_KEY, String(next));
    } catch {
      // sessionStorage puede no estar disponible en algunos contextos
    }
  };

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
      name: 'Cocina',
      path: '/admin/cocina',
      icon: ChefHat,
      roles: ['COCINA', 'ADMIN']
    },
    {
      name: 'Cajero',
      path: '/admin/cajero',
      icon: Banknote,
      roles: ['CAJERO', 'ADMIN']
    },
    { 
      name: 'Usuarios', 
      path: '/admin/usuarios', 
      icon: Users, 
      roles: ['ADMIN'] 
    }
  ];

  return (
    <div className="flex h-screen overflow-hidden dark">
      {/* Sidebar / Menú Lateral */}
      <aside className={`
        bg-slate-900 text-white flex flex-col z-20 shadow-xl
        transition-all duration-300 ease-in-out
        ${collapsed ? 'w-[72px]' : 'w-64'}
      `}>
        
        {/* Header: Logo + Toggle */}
        <div className={`
          border-b border-slate-800 bg-slate-950
          flex items-center gap-2
          ${collapsed ? 'justify-center p-4' : 'justify-between p-6'}
        `}>
          {/* Logo: completo cuando expandido, corto cuando colapsado */}
          {!collapsed ? (
            <Link 
              to="/" 
              className="text-xl font-black tracking-tight hover:text-orange-500 transition-colors"
            >
              FOOD<span className="text-orange-500">STORE</span>
            </Link>
          ) : (
            <Link 
              to="/" 
              className="text-lg font-black text-orange-500 hover:text-orange-400 transition-colors"
              title="FoodStore"
            >
              FS
            </Link>
          )}

          {/* Botón para colapsar/expandir */}
          {!collapsed && (
            <button
              onClick={toggleSidebar}
              className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              title="Minimizar menú"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Botón para expandir (solo visible cuando está colapsado) */}
        {collapsed && (
          <div className="flex justify-center p-3 border-b border-slate-800">
            <button
              onClick={toggleSidebar}
              className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              title="Expandir menú"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* NAVEGACIÓN FILTRADA POR ROLES (RBAC CORPORATIVO) */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems
            .filter(item => 
              user?.roles?.some((uRol: any) => item.roles.includes(uRol.codigo || uRol.rol_codigo))
            )
            .map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  title={collapsed ? item.name : undefined}
                  className={`
                    flex items-center gap-3 py-3 rounded-xl transition-all duration-200
                    ${isActive 
                      ? 'bg-orange-600 text-white shadow-lg shadow-orange-600/20' 
                      : 'text-slate-400 hover:bg-slate-800 hover:text-white'}
                    ${collapsed ? 'justify-center px-0' : 'px-4'}
                  `}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  {!collapsed && (
                    <span className="font-medium truncate">{item.name}</span>
                  )}
                </Link>
              );
            })}
        </nav>

        {/* Perfil del Empleado y Cerrar Sesión */}
        <div className={`
          border-t border-slate-800 bg-slate-900/50 flex flex-col gap-2
          ${collapsed ? 'p-3 items-center' : 'p-4'}
        `}>
          {/* Info de usuario y logout */}
          <div className={`flex items-center gap-2 ${collapsed ? 'flex-col' : ''}`}>
            {!collapsed && (
              <div className="overflow-hidden flex-1">
                <p className="text-sm font-bold truncate">{user?.nombre || 'Usuario'}</p>
                <p className="text-[10px] text-orange-400 font-bold uppercase tracking-wider truncate">
                  {user?.roles?.map((r: any) => r.nombre.replace('_', ' ')).join(', ')}
                </p>
              </div>
            )}
            <button 
              onClick={handleLogout} 
              className={`text-slate-500 hover:text-red-500 p-2 transition-colors shrink-0 ${collapsed ? 'mt-1' : ''}`}
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