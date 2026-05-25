import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
  // Necesario para que el navegador envíe y reciba la cookie httpOnly del login
  withCredentials: true,
});

// INTERCEPTOR DE PETICIONES (Agrega el Token directo del LocalStorage)
api.interceptors.request.use(
  (config) => {
    let token = null;

    // 1. Leemos directamente del Local Storage para evitar el delay de Zustand
    const authStorageStr = localStorage.getItem('auth-store'); 
    
    if (authStorageStr) {
      try {
        const parsedData = JSON.parse(authStorageStr);
        token = parsedData.state?.token;
      } catch (error) {
        console.error("Error parseando el token", error);
      }
    }

    // 2. Fallback: Si no lo encontró en Local Storage, intentamos con el Store
    if (!token) {
      token = useAuthStore.getState().token;
    }
    
   if (token && config.headers) {
      // Le avisamos a la consola para auditar
      console.log("🔑 [AXIOS] Enviando petición a:", config.url, "con token:", token.substring(0, 15) + "...");
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      console.warn("⚠️ [AXIOS] CUIDADO: Haciendo petición SIN TOKEN a:", config.url);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// INTERCEPTOR DE RESPUESTAS (Maneja token expirado → redirige al login)
api.interceptors.response.use(
  (response) => response, // Respuestas 2xx pasan directo
  (error) => {
    if (error.response?.status === 401) {
      console.warn('⛔ [AXIOS] Token expirado o inválido. Cerrando sesión...');
      // Limpiamos el store de autenticación
      useAuthStore.getState().logout();
      // Redirigimos al login sin recargar toda la SPA
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;