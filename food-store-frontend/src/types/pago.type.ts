// src/types/pago.type.ts
// Tipos de la integración MercadoPago, alineados con los schemas del backend.

export type MpStatus = 'pending' | 'approved' | 'rejected' | 'cancelled' | 'refunded';

export interface Pago {
  id:                 number;
  pedido_id:          number;
  mp_payment_id:      number | null;
  mp_status:          MpStatus;
  mp_status_detail:   string | null;
  transaction_amount: number;
  payment_method_id:  string | null;
  external_reference: string;
  idempotency_key:    string;
  preference_id:      string | null;
  init_point:         string | null;
  creado_en:          string;
  actualizado_en:     string | null;
}

export interface CrearPagoRequest {
  pedido_id: number;
}
