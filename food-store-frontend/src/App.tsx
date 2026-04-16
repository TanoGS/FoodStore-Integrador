import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from './pages/login';
import { HomePage } from './pages/home';
import { RegisterPage } from './pages/register';
import { ProtectedRoute } from './app/router/ProtectedRoute';

// Panel temporal
const AdminTempDashboard = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <h1 className="text-4xl font-bold text-gray-800">¡Bienvenido al Panel de Administración!</h1>
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Ruta principal (Catálogo Público) */}
        <Route path="/" element={<HomePage />} />
        
        {/* Ruta de inicio de sesión */}
        <Route path="/login" element={<LoginPage />} />

        <Route path="/register" element={<RegisterPage />} />
        
        {/* Rutas del Admin */}
        <Route path="/admin/*" element={<AdminTempDashboard />} />

        {/* RUTAS PROTEGIDAS PARA EL ADMIN */}
        <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
          <Route path="/admin/*" element={<AdminTempDashboard />} />
        </Route>
        
        {/* Redirección por defecto */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;