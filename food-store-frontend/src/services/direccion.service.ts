import api from '../config/axios';

// ── Interfaces alineadas con el backend ────────────────────────────────────
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

export interface CrearDireccionPayload {
  alias?:         string;
  calle:          string;
  numero:         string;
  piso?:          string;
  departamento?:  string;
  ciudad:         string;
  codigo_postal:  string;
  predeterminada: boolean;
}

export const DireccionService = {
  listar: async (): Promise<Direccion[]> => {
    const { data } = await api.get('/direcciones');
    return data;
  },

  crear: async (payload: CrearDireccionPayload): Promise<Direccion> => {
    const { data } = await api.post('/direcciones', payload);
    return data;
  },

  actualizar: async (id: number, payload: Partial<CrearDireccionPayload>): Promise<Direccion> => {
    const { data } = await api.patch(`/direcciones/${id}`, payload);
    return data;
  },

  marcarPredeterminada: async (id: number): Promise<Direccion> => {
    const { data } = await api.patch(`/direcciones/${id}/principal`);
    return data;
  },

  eliminar: async (id: number): Promise<void> => {
    await api.delete(`/direcciones/${id}`);
  },
};
