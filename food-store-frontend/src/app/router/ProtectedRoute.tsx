import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

interface Props {
  allowedRoles: string[];
}

export const ProtectedRoute = ({ allowedRoles }: Props) => {
  const { isAuthenticated, user } = useAuthStore();

  // 1. Si no está logueado, al login
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // 2. Si está logueado pero su rol no está en la lista permitida, a la home
  if (!allowedRoles.includes(user?.rol_nombre)) {
    alert("No tienes permisos para acceder a esta sección");
    return <Navigate to="/" replace />;
  }

  // 3. Si todo está ok, renderiza los hijos (el panel admin)
  return <Outlet />;
};