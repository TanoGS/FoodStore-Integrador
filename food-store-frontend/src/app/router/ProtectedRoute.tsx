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

  // 2. Si está logueado pero ninguno de sus roles está en la lista permitida, a la home
  const userRoleCodigos = user?.roles?.map((r: any) => r.codigo) ?? [];
  const tienePermiso = allowedRoles.some(rol => userRoleCodigos.includes(rol));

  if (!tienePermiso) {
    return <Navigate to="/" replace />;
  }

  // 3. Si todo está ok, renderiza los hijos (el panel admin)
  return <Outlet />;
};