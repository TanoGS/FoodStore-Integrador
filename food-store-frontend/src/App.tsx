import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Home from './pages/Home';

import Login from './pages/auth/Login';
import AdminLayout from './components/layout/AdminLayout';
import ProductosAdmin from './pages/admin/ProductosAdmin';
import CategoriasAdmin from './pages/admin/CategoriasAdmin';
import IngredientesAdmin from './pages/admin/IngredientesAdmin';
import PanelUsuarios from './pages/admin/PanelUsuarios';
import Register from './pages/auth/Register';
import MisDirecciones from './pages/direcciones/MisDirecciones';
import GestorPedidos from './pages/admin/GestorPedidos';
import Checkout from './pages/Checkout';
import PedidoExitoso from './pages/PedidoExitoso';
import MisPedidos from './pages/client/MisPedidos';
import MiPerfil   from './pages/client/MiPerfil';
import { ProtectedRoute } from './app/router/ProtectedRoute';

const ADMIN_ROLES = ['ADMIN', 'GESTOR_STOCK', 'GESTOR_PEDIDOS'];

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
            <Route index element={<div className="text-2xl font-bold">Bienvenido al Dashboard de Gestión</div>} />
            <Route path="productos" element={<ProductosAdmin />} />
            <Route path="categorias" element={<CategoriasAdmin />} />
            <Route path="ingredientes" element={<IngredientesAdmin />} />
            <Route path="gestor-pedidos" element={<GestorPedidos />} />
            <Route path="usuarios" element={<PanelUsuarios />} />
          </Route>
        </Route>

      </Routes>
    </BrowserRouter>
  );
}