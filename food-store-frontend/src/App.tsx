import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Home from './pages/Home';
import Catalogo from './pages/client/Catalogo';

// Componente placeholder para el catálogo temporal
const CatalogoPlaceholder = () => <div className="p-10 text-center text-2xl font-bold">Catálogo en construcción 🚧</div>;

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* El Layout envuelve todas estas rutas */}
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          
          <Route path="carrito" element={<div className="p-10 text-center text-2xl">Carrito en construcción 🛒</div>} />
          <Route path="login" element={<div className="p-10 text-center text-2xl">Login en construcción 🔐</div>} />
          
          <Route path="catalogo" element={<Catalogo />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}