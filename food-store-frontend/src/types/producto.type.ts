import type { Categoria } from './categoria.type';

export interface IngredienteBreve {
  id: number;
  nombre: string;
  unidad_medida: string;
  es_alergeno: boolean;
}

export interface RecetaItem {
  ingrediente_id: number;
  cantidad_requerida: number;
  es_removible: boolean;
  ingrediente: IngredienteBreve;
}

export interface Producto {
  id: number;
  nombre: string;
  descripcion?: string;
  precio: number;
  /** Alias de `precio` para compatibilidad con componentes que usan `precio_base`. */
  precio_base?: number;
  /** Stock disponible del producto (stock_cantidad del backend). */
  stock_cantidad?: number;
  /** Alias para `stock_cantidad` para compatibilidad con componentes que usan `stock_disponible`. */
  stock_disponible?: number;
  imagen_url?: string | null;
  categorias?: Categoria[];
  activo?: boolean;
  receta_detallada?: RecetaItem[];
}
