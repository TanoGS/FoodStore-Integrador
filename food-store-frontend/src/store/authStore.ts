import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { useCartStore } from './cartStore';

// Estructura de rol tal como la devuelve el backend (UsuarioPublic > RolPublic)
export interface RolPublic {
  codigo: string;  // 'ADMIN' | 'GESTOR_STOCK' | 'GESTOR_PEDIDOS' | 'CLIENTE'
  nombre: string;
  descripcion?: string;
}

export interface User {
  id: number;
  email: string;
  nombre: string;
  apellido?: string;
  cel?: string;
  activo?: boolean;
  roles?: RolPublic[];
}

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  
  // Acciones
  setLogin:   (token: string, user: User) => void;
  logout:     () => void;
  updateUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,

      setLogin: (token, user) => {
        // Restaura el carrito guardado de este usuario, si existe
        const saved = localStorage.getItem(`food-store-cart-${user.id}`);
        if (saved) {
          try { useCartStore.getState().setItems(JSON.parse(saved)); }
          catch { /* ignorar si el JSON está corrupto */ }
        } else {
          useCartStore.getState().clearCart();
        }
        set({ token, user, isAuthenticated: true });
      },
      logout: () => {
        const { user } = useAuthStore.getState();
        if (user) {
          // Persiste el carrito actual bajo la key del usuario
          const items = useCartStore.getState().items;
          localStorage.setItem(`food-store-cart-${user.id}`, JSON.stringify(items));
        }
        useCartStore.getState().clearCart();
        set({ token: null, user: null, isAuthenticated: false });
      },
      updateUser: (user) => set({ user }),
    }),
    {
      name: 'food-store-auth', // Se guarda en localStorage
    }
  )
);