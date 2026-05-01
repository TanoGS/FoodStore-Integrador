import { type Categoria } from './categoria.type';

export interface Producto {
  id: number;
  nombre: string;
  descripcion?: string;
  precio_base: number;
  es_personalizable: boolean;
  imagen_url?: string | null;
  stock_disponible: number;
  activo: boolean;
  categorias?: Categoria[]; // Relación N:M
}