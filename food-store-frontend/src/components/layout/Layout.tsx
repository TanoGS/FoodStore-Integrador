import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Navbar />
      {/* Outlet renderiza la página actual (Home, Catálogo, etc.) */}
      <main className="flex-grow">
        <Outlet />
      </main>
      
      {/* Footer básico */}
      <footer className="bg-gray-800 text-white py-6 text-center">
        <p>© 2026 FoodStore. Todos los derechos reservados.</p>
      </footer>
    </div>
  );
}