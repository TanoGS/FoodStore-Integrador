import { create } from 'zustand';
import { axiosClient } from '../api/axios';

interface AuthState {
  isAuthenticated: boolean;
  user: any | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  user: null,
  loading: false,
  error: null,

  login: async (email, password) => {
    set({ loading: true, error: null });
    try {
      // Llamada real al backend
      const response = await axiosClient.post('/usuarios/login', { email, password });
      
      set({ 
        isAuthenticated: true, 
        user: response.data, 
        loading: false 
      });
    } catch (err: any) {
      set({ 
        error: err.response?.data?.detail || 'Error al iniciar sesión', 
        loading: false 
      });
      throw err; // Re-lanzamos para que el componente pueda manejarlo si quiere
    }
  },

  logout: () => set({ isAuthenticated: false, user: null, error: null }),
}));