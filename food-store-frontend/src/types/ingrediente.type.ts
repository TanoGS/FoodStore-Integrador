export interface Ingrediente {
  id: number;
  nombre: string;
  precio_adicional: number;
  es_alergeno: boolean;
  activo?: boolean;
}