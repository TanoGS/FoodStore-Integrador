import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { useCartStore } from './cartStore';
import { wsService } from '../services/websocket.service';

// Re-export para no romper imports existentes
export type { Rol, Usuario } from '../types/auth.type';
import type { Usuario } from '../types/auth.type';

// User del store = Usuario del backend (alias para claridad)
export type User = Usuario;

interface AuthState {
  user:  User | null;
  token: string | null;
  isAuthenticated: boolean;

  // Acciones
  setLogin:   (user: User, token: string) => void;
  logout:     () => void;
  updateUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      setLogin: (user, token) => {
        // Restaura el carrito guardado de este usuario, si existe
        const saved = localStorage.getItem(`food-store-cart-${user.id}`);
        if (saved) {
          try { useCartStore.getState().setItems(JSON.parse(saved)); }
          catch { /* ignorar si el JSON está corrupto */ }
        } else {
          useCartStore.getState().clearCart();
        }
        set({ user, token, isAuthenticated: true });

        // Abre la conexión WebSocket de pedidos con el token JWT.
        // El token también se persiste en sessionStorage para poder
        // reabrir el WS tras un F5 (onRehydrateStorage).
        wsService.connect(token);
        wsService.onAuthError(() => {
          console.warn('[auth] WS reportó token inválido; cerrando sesión');
          useAuthStore.getState().logout();
        });
      },
      logout: () => {
        const { user } = useAuthStore.getState();
        if (user) {
          const items = useCartStore.getState().items;
          localStorage.setItem(`food-store-cart-${user.id}`, JSON.stringify(items));
        }
        useCartStore.getState().clearCart();
        wsService.disconnect();
        set({ user: null, token: null, isAuthenticated: false });
      },
      updateUser: (user) => set({ user }),
    }),
    {
      name: 'food-store-auth',
      storage: createJSONStorage(() => sessionStorage),
      // Persistimos token + user + isAuthenticated para poder reabrir
      // el WebSocket tras un F5 sin necesidad de un nuevo login.
      // sessionStorage muere al cerrar la tab (más seguro que localStorage).
      partialize: (state) => ({
        user:             state.user,
        token:            state.token,
        isAuthenticated:   state.isAuthenticated,
      }),

      // Al rehidratar (p. ej. F5), si había sesión persistida,
      // reabrimos el WebSocket con el token guardado en sessionStorage.
      onRehydrateStorage: () => (state) => {
        if (state?.token && state?.isAuthenticated) {
          // eslint-disable-next-line no-console
          console.info('[auth] Rehidratando WS con token persistido');
          wsService.connect(state.token);
          // Re-registrar el callback de auth error (no se persiste
          // entre recargas porque vive en el closure del singleton).
          wsService.onAuthError(() => {
            console.warn('[auth] WS reportó token inválido; cerrando sesión');
            useAuthStore.getState().logout();
          });
        }
      },
    }
  )
);
