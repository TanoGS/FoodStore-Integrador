import type { Producto } from "./producto.type";

export interface Categoria {
  id: number;
  nombre: string;
  descripcion?: string;
  padre_id?: number | null;
  eliminado_en?: string | null;

  productos?: Producto[]; 
}