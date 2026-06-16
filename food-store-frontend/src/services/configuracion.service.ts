import api from '../config/axios';

export interface CostoEnvioResponse {
  costo_envio_delivery: number;
}

export const ConfiguracionService = {
  /** Obtiene el costo de envío actual para pedidos DELIVERY. */
  getCostoEnvio: async (): Promise<CostoEnvioResponse> => {
    const res = await api.get<CostoEnvioResponse>('/admin/configuracion/costo-envio');
    return res.data;
  },

  /** Actualiza el costo de envío global. Solo ADMIN / GESTOR_PEDIDOS. */
  setCostoEnvio: async (costo: number): Promise<CostoEnvioResponse> => {
    const res = await api.patch<CostoEnvioResponse>('/admin/configuracion/costo-envio', {
      costo_envio_delivery: costo,
    });
    return res.data;
  },
};
