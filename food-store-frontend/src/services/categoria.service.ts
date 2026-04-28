import api from '../config/axios';
import { type Categoria } from '../types/categoria.type';
import { type Producto } from '../types/producto.type';

// Definimos la interfaz para una categoría que incluya sus productos
export interface CategoriaConProductos extends Categoria {
  productos: Producto[];
}

export const CategoriaService = {
  async listarConProductos(): Promise<CategoriaConProductos[]> {
    const { data } = await api.get('/categorias/con-productos');
    
    // Desempaquetamos si viene paginado { data: [...], total: X }
    const lista = data?.data || data;
    
    if (Array.isArray(lista)) {
      // Opcional: Filtrar categorías que no tengan productos para no mostrar títulos vacíos
      return lista.filter(cat => cat.productos && cat.productos.length > 0);
    }
    
    return [];
  }
};