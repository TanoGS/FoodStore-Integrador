// src/types/direccion.type.ts
// Tipos del módulo DireccionEntrega, alineados con los schemas del backend.

export interface Direccion {
  id:             number;
  usuario_id:     number;
  alias?:         string | null;
  calle:          string;
  numero:         string;
  piso?:          string | null;
  departamento?:  string | null;
  ciudad:         string;
  codigo_postal:  string;
  predeterminada: boolean;
  creado_en:      string;
  actualizado_en: string;
  eliminado_en?:  string | null;
}

export interface CrearDireccionRequest {
  alias?:         string;
  calle:          string;
  numero:         string;
  piso?:          string;
  departamento?:  string;
  ciudad:         string;
  codigo_postal:  string;
  predeterminada: boolean;
}

export type ActualizarDireccionRequest = Partial<CrearDireccionRequest>;
