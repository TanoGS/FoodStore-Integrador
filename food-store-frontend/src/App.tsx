import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Home from './pages/Home';

import Login from './pages/auth/Login';
import AdminLayout from './components/layout/AdminLayout';
import Dashboard from './pages/admin/Dashboard';
import ProductosAdmin from './pages/admin/ProductosAdmin';
import CategoriasAdmin from './pages/admin/CategoriasAdmin';
import IngredientesAdmin from './pages/admin/IngredientesAdmin';
import PanelUsuarios from './pages/admin/PanelUsuarios';
import Register from './pages/auth/Register';
import MisDirecciones from './pages/direcciones/MisDirecciones';
import GestorPedidos from './pages/admin/GestorPedidos';
import VistaCocina   from './pages/admin/VistaCocina';
import VistaCajero   from './pages/admin/VistaCajero';
import Checkout from './pages/Checkout';
import PedidoExitoso from './pages/PedidoExitoso';
import MisPedidos from './pages/client/MisPedidos';
import MiPerfil   from './pages/client/MiPerfil';
import { ProtectedRoute } from './app/router/ProtectedRoute';
import { useAuthStore } from './store/authStore';

const ADMIN_ROLES = ['ADMIN', 'GESTOR_STOCK', 'GESTOR_PEDIDOS', 'COCINA', 'CAJERO'];

/**
 * Redirige según el rol principal del usuario cuando entra a /admin:
 *  - COCINA      → /admin/cocina     (KDS directo)
 *  - CAJERO      → /admin/cajero    (Caja directo)
 *  - GESTOR_STOCK→ /admin/productos  (Gestión de stock)
 *  - ADMIN / GESTOR_PEDIDOS → Dashboard con gráficos
 */
function AdminIndexRedirect() {
  const { user } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    const roles = (user?.roles ?? []).map((r: any) => r.codigo || r.rol_codigo);

    if (roles.includes('COCINA')) {
      navigate('/admin/cocina', { replace: true });
      return;
    }
    if (roles.includes('CAJERO')) {
      navigate('/admin/cajero', { replace: true });
      return;
    }
    if (roles.includes('GESTOR_STOCK')) {
      navigate('/admin/productos', { replace: true });
      return;
    }
  }, [user, navigate]);

  return <Dashboard />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>

        {/* --- RUTAS PÚBLICAS (Cliente) --- */}
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="carrito" element={<div className="p-10 text-center text-2xl">Carrito en construcción 🛒</div>} />
          <Route path="/registro" element={<Register />} />
          <Route path="/mis-direcciones" element={<MisDirecciones />} />
          <Route path="/mi-perfil"       element={<MiPerfil />} />
          <Route path="/mis-pedidos" element={<MisPedidos />} />
          <Route path="/checkout" element={<Checkout />} />
          {/* Ruta dinámica: :pedidoId es el parámetro que lee useParams */}
          <Route path="/pedido-exitoso/:pedidoId" element={<PedidoExitoso />} />
        </Route>

        <Route path="login" element={<Login />} />

        {/* --- RUTAS PROTEGIDAS (Admin / Gestor) --- */}
        <Route element={<ProtectedRoute allowedRoles={ADMIN_ROLES} />}>
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminIndexRedirect />} />
            <Route path="productos" element={<ProductosAdmin />} />
            <Route path="categorias" element={<CategoriasAdmin />} />
            <Route path="ingredientes" element={<IngredientesAdmin />} />
            <Route path="pedidos" element={<GestorPedidos />} />
            <Route path="cocina"  element={<VistaCocina />} />
            <Route path="cajero"  element={<VistaCajero />} />
            <Route path="usuarios" element={<PanelUsuarios />} />
          </Route>
        </Route>

      </Routes>
    </BrowserRouter>
  );
}
