import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { useCartStore } from './cartStore';
import { wsService } from '../services/websocket.service';

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

        // Abre (o reclama liderazgo para) la conexión WebSocket de pedidos.
        wsService.connect(token);
        // Si el servidor rechaza el token en algún momento, el WS nos avisa
        // y forzamos un logout limpio.
        wsService.onAuthError(() => {
          console.warn('[auth] WS reportó token inválido; cerrando sesión');
          useAuthStore.getState().logout();
        });
      },
      logout: () => {
        const { user } = useAuthStore.getState();
        if (user) {
          // Persiste el carrito actual bajo la key del usuario
          const items = useCartStore.getState().items;
          localStorage.setItem(`food-store-cart-${user.id}`, JSON.stringify(items));
        }
        useCartStore.getState().clearCart();

        // Cierra la conexión WS y libera el liderazgo
        wsService.disconnect();

        set({ token: null, user: null, isAuthenticated: false });
      },
      updateUser: (user) => set({ user }),
    }),
    {
      name: 'food-store-auth',
      // sessionStorage en vez de localStorage → cada pestaña del
      // browser tiene su propio estado de auth. Permite tener N
      // pestañas con N usuarios distintos (o repetidos) sin que
      // se pisen entre sí. Persiste entre refreshes de la misma
      // tab, se pierde al cerrar la tab (intencional para multi-user).
      storage: createJSONStorage(() => sessionStorage),

      // Al rehidratar el estado (p. ej. F5), si había una sesión
      // persistida, el store queda con token + isAuthenticated=true,
      // pero la conexión WebSocket NO se reabre sola (porque
      // setLogin solo corre en el login real). Sin este callback,
      // después de un refresh las vistas (cajero, cocina, MisPedidos,
      // etc.) se montan y se suscriben a un WS que está cerrado,
      // y por lo tanto nunca reciben los eventos en tiempo real.
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
