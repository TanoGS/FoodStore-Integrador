import api from '../config/axios';
import { type Producto } from '../types/producto.type';

export const ProductoService = {
  async listarActivos(): Promise<Producto[]> {
    const { data } = await api.get('/productos/');
    
    // CASO 1: Si FastAPI devuelve un formato paginado { data: [...], total: X }
    if (data && Array.isArray(data.data)) {
      return data.data;
    }
    
    // CASO 2: Si FastAPI devuelve la lista directamente [...]
    if (Array.isArray(data)) {
      return data;
    }

    // Si viene algo raro o vacío, devolvemos un arreglo vacío por seguridad
    return [];
  },

  async obtenerPorId(id: number): Promise<Producto> {
    const { data } = await api.get(`/productos/${id}`);
    return data;
  }
};