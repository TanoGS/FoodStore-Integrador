import api from '../config/axios';

export interface PagoResponse {
  id: number;
  pedido_id: number;
  mp_status: string;
  mp_status_detail: string | null;
  transaction_amount: number;
  payment_method_id: string | null;
  external_reference: string;
  preference_id: string | null;
  init_point: string | null;
  creado_en: string;
  actualizado_en: string | null;
}

export const PagosService = {
  /** Crea una preference de pago en MP. Devuelve el init_point. */
  crear: async (pedidoId: number): Promise<PagoResponse> => {
    const res = await api.post<PagoResponse>('/pagos/crear', { pedido_id: pedidoId });
    return res.data;
  },

  /** Consulta el estado del pago de un pedido. */
  obtenerPorPedido: async (pedidoId: number): Promise<PagoResponse> => {
    const res = await api.get<PagoResponse>(`/pagos/${pedidoId}`);
    return res.data;
  },

  /**
   * Consulta el estado real del pago en MercadoPago y actualiza el registro local.
   * Para uso del staff (cajero/admin): permite verificar manualmente si el pago
   * fue aprobado cuando el webhook no llegó o llegó tarde.
   * Requiere token JWT con rol ADMIN / GESTOR_PEDIDOS / CAJERO.
   */
  sincronizar: async (pedidoId: number): Promise<PagoResponse> => {
    const res = await api.post<PagoResponse>(`/pagos/${pedidoId}/sincronizar`);
    return res.data;
  },
};
