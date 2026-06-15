
import axios from '../config/axios';

export const CatalogoService = {
  // ==========================================
  // CATEGORÍAS
  // ==========================================
  getCategorias: async () => {
    const res = await axios.get('/catalogo/categorias');
    return res.data;
  },

  // Incluye las dadas de baja (para el panel admin)
  getCategoriasTodas: async () => {
    const res = await axios.get('/catalogo/categorias?incluir_eliminados=true&solo_raiz=false');
    return res.data;
  },

  crearCategoria: async (payload: any) => {
    const res = await axios.post('/catalogo/categorias', payload);
    return res.data;
  },

  actualizarCategoria: async (id: number, payload: any) => {
    const res = await axios.patch(`/catalogo/categorias/${id}`, payload);
    return res.data;
  },

  toggleVisibilidadCategoria: async (id: number, activo: boolean) => {
    const res = await axios.patch(`/catalogo/categorias/${id}/visibilidad?activo=${activo}`);
    return res.data;
  },

  eliminarCategoria: async (id: number) => {
    await axios.delete(`/catalogo/categorias/${id}`);
  },

  reactivarCategoria: async (id: number) => {
    const res = await axios.patch(`/catalogo/categorias/${id}/reactivar`);
    return res.data;
  },

  // ==========================================
  // PRODUCTOS (RECETAS / ESCANDALLOS)
  // ==========================================
  getProductos: async () => {
    const res = await axios.get('/catalogo/productos');
    return res.data;
  },

  // Incluye los dados de baja (para el panel admin)
  getProductosTodos: async () => {
    const res = await axios.get('/catalogo/productos?incluir_eliminados=true');
    return res.data;
  },

  getProductoById: async (id: number) => {
    const res = await axios.get(`/catalogo/productos/${id}`);
    return res.data;
  },

  crearProducto: async (payload: any) => {
    const res = await axios.post('/catalogo/productos', payload);
    return res.data;
  },

  actualizarProducto: async (id: number, payload: any) => {
    const res = await axios.patch(`/catalogo/productos/${id}`, payload);
    return res.data;
  },

  toggleDisponibilidad: async (id: number, activo: boolean) => {
    const res = await axios.patch(`/catalogo/productos/${id}/disponibilidad?activo=${activo}`);
    return res.data;
  },

  eliminarProducto: async (id: number) => {
    await axios.delete(`/catalogo/productos/${id}`);
  },

  reactivarProducto: async (id: number) => {
    const res = await axios.patch(`/catalogo/productos/${id}/reactivar`);
    return res.data;
  },

  // ==========================================
  // INGREDIENTES
  // ==========================================
  getIngredientes: async () => {
    const res = await axios.get('/catalogo/ingredientes');
    return res.data;
  },

  // Incluye los dados de baja (para el panel admin)
  getIngredientesTodos: async () => {
    const res = await axios.get('/catalogo/ingredientes?incluir_eliminados=true');
    return res.data;
  },

  crearIngrediente: async (payload: any) => {
    const res = await axios.post('/catalogo/ingredientes', payload);
    return res.data;
  },

  actualizarIngrediente: async (id: number, payload: any) => {
    const res = await axios.patch(`/catalogo/ingredientes/${id}`, payload);
    return res.data;
  },

  eliminarIngrediente: async (id: number) => {
    await axios.delete(`/catalogo/ingredientes/${id}`);
  },

  reactivarIngrediente: async (id: number) => {
    const res = await axios.patch(`/catalogo/ingredientes/${id}/reactivar`);
    return res.data;
  },
};