import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  // withCredentials: true → el navegador envía automáticamente la cookie
  // HttpOnly `access_token` en cada request. Además se añade el header
  // Authorization explícito (ver interceptor abajo) para que el backend
  // priorice el token de esta pestaña y no la cookie compartida entre tabs.
  withCredentials: true,
});

// ─── Interceptor de requests: adjuntar token de sessionStorage ────────────────
// Las cookies son compartidas entre pestañas del mismo navegador, pero
// sessionStorage es por-pestaña. Si el usuario tiene sesiones distintas en
// distintas pestañas (ej. ADMIN en una, CLIENTE en otra), sin este interceptor
// el backend recibe la cookie de la última sesión iniciada (no la de esta tab).
// Enviando el token como Authorization header, el backend puede priorizar el
// JWT correcto correspondiente a esta pestaña.
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers = config.headers ?? {};
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// ─── Interceptor de respuestas: refresh automático ────────────────────────────
// Cuando el servidor devuelve 401, intentamos renovar el access token usando
// la cookie `refresh_token` (HttpOnly, enviada automáticamente). Si el refresh
// falla → logout.

let _isRefreshing = false;
let _refreshQueue: Array<(ok: boolean) => void> = [];

function _processQueue(ok: boolean) {
  _refreshQueue.forEach((cb) => cb(ok));
  _refreshQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    // Solo actuar en 401, y no en la propia ruta de refresh/login/logout.
    const isAuthRoute = ['/usuarios/login', '/usuarios/refresh', '/usuarios/logout']
      .some((path) => original?.url?.includes(path));

    if (error.response?.status === 401 && !isAuthRoute && !original._retry) {
      if (_isRefreshing) {
        // Ya hay un refresh en curso — encolar y esperar resultado.
        return new Promise((resolve, reject) => {
          _refreshQueue.push((ok) => {
            if (ok) resolve(api(original));
            else reject(error);
          });
        });
      }

      original._retry = true;
      _isRefreshing = true;

      try {
        // Intentar renovar. La cookie `refresh_token` va automáticamente.
        await api.post('/usuarios/refresh');
        _processQueue(true);
        return api(original); // reintentar el request original
      } catch {
        _processQueue(false);
        useAuthStore.getState().logout();
        window.location.href = '/login';
        return Promise.reject(error);
      } finally {
        _isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;