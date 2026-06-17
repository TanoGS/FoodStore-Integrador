// src/types/pedido.type.ts
// Tipos canónicos del dominio Pedido, alineados con los schemas del backend.

export interface DetallePedido {
  detalle_id:              number;
  producto_id:             number;
  cantidad:                number;
  nombre_snapshot:         string;
  precio_snapshot:         number;
  subtotal_snap:           number;
  personalizacion:         number[] | null;
  personalizacion_nombres: string[] | null;
}

export type EstadoPedido =
  | 'PENDIENTE'
  | 'CONFIRMADO'
  | 'EN_PREPARACION'
  | 'EN_CAMINO'
  | 'ENTREGADO'
  | 'CANCELADO';

export type FormaPago = 'EFECTIVO' | 'MERCADOPAGO';
export type TipoEntrega = 'EN_LOCAL' | 'DELIVERY';

export interface HistorialEstado {
  id:            number;
  pedido_id:     number;
  estado_desde:  EstadoPedido | null;
  estado_hacia:  EstadoPedido;
  usuario_id:    number | null;
  motivo:        string | null;
  creado_en:     string;
}

export interface Pedido {
  id:                number;
  usuario_id:        number;
  direccion_id:      number | null;
  estado_codigo:     EstadoPedido;
  forma_pago_codigo: FormaPago;
  tipo_entrega:      TipoEntrega;
  subtotal:          number;
  descuento:         number;
  costo_envio:       number;
  total:             number;
  notas:             string | null;
  creado_en:         string;
  actualizado_en:    string | null;
  detalles:          DetallePedido[];
  historial:         HistorialEstado[];
}

export interface PedidoList {
  data:  Pedido[];
  total: number;
}

export interface CrearPedidoRequest {
  detalles: {
    producto_id:    number;
    cantidad:       number;
    personalizacion?: number[];
  }[];
  forma_pago_codigo: FormaPago;
  tipo_entrega:      TipoEntrega;
  direccion_id?:     number | null;
  notas?:            string;
}

export interface AvanzarEstadoRequest {
  estado_hacia: EstadoPedido;
  motivo?:      string;
}
