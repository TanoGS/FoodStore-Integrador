import { useAuthStore } from '../store/authStore';

/**
 * Hook centralizado para verificar roles en la UI.
 * Lee del authStore para determinar qué puede ver/hacer el usuario logueado.
 */
export function useRole() {
  const user = useAuthStore((state) => state.user);

  // Extraemos los códigos de rol del array de objetos { codigo, nombre }
  const roles = user?.roles?.map((r) => r.codigo) ?? [];

  return {
    isAdmin:        roles.includes('ADMIN'),
    isGestorStock:  roles.includes('GESTOR_STOCK'),
    isGestorPedidos:roles.includes('GESTOR_PEDIDOS'),
    isCocina:       roles.includes('COCINA'),
    isCliente:      roles.includes('CLIENTE'),
    // Admin puede todo; Gestor de Stock puede crear/editar productos, categorías, ingredientes
    puedeEditar:    roles.includes('ADMIN') || roles.includes('GESTOR_STOCK'),
    roles,
  };
}
