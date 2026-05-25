import axios from 'axios';
import { useAuthStore } from '../store/authStore';

// URL base de tu backend
const API_URL = 'http://127.0.0.1:8000/api/usuarios';

// Helper para obtener los headers con el token
const getAuthHeaders = () => {
  const token = useAuthStore.getState().token;
  return { headers: { Authorization: `Bearer ${token}` } };
};

export const UsuarioService = {
  listar: async () => {
    const response = await axios.get(`${API_URL}/gestion`, getAuthHeaders());
    return response.data; // { data: [...], total: X }
  },

  crear: async (datos: any) => {
    const response = await axios.post(`${API_URL}/registro`, datos, getAuthHeaders());
    return response.data;
  },

  eliminar: async (id: number) => {
    const response = await axios.delete(`${API_URL}/${id}`, getAuthHeaders());
    return response.data;
  },

  reactivar: async (id: number) => {
    const response = await axios.patch(`${API_URL}/${id}/reactivar`, {}, getAuthHeaders());
    return response.data;
  }
};