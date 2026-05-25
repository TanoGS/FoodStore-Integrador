import api from '../config/axios';

// Detalle individual dentro de un pedido
export interface DetallePedidoPublic {
  producto_id:     number;
  cantidad:        number;
  nombre_snapshot: string;
  precio_snapshot: number;
  subtotal_snap:   number;
}

// Molde completo del pedido (fiel al backend: PedidoPublic)
export interface PedidoPublic {
  id:                number;
  usuario_id:        number;
  direccion_id?:     number | null;
  estado_codigo:     string;  // 'PENDIENTE' | 'CONFIRMADO' | 'EN_PREPARACION' | ...
  forma_pago_codigo: string;
  subtotal:          number;
  descuento:         number;
  costo_envio:       number;
  total:             number;
  notas?:            string | null;
  creado_en:         string;
  actualizado_en?:   string | null;
  detalles:          DetallePedidoPublic[];
}

// Alias para compatibilidad con componentes existentes
export type Pedido = PedidoPublic;

// Molde para los items que enviamos al comprar
export interface PedidoItemPayload {
  producto_id: number;
  cantidad: number;
}

// Molde exacto del payload de creación
export interface CrearPedidoPayload {
  direccion_id: number;
  items: PedidoItemPayload[];
}

export const PedidoService = {
  // Admin/Gestor: trae todos. Cliente: solo los suyos. El backend filtra por rol.
  listarTodos: async (): Promise<PedidoPublic[]> => {
    const { data } = await api.get('/pedidos/');
    return data.data || data;
  },

  // Alias semántico para la pantalla del cliente (llama al mismo endpoint)
  listarMisPedidos: async (): Promise<PedidoPublic[]> => {
    const { data } = await api.get('/pedidos/');
    return data.data || data;
  },

  // Cambia el estado del pedido
  actualizarEstado: async (id: number, nuevoEstado: string): Promise<Pedido> => {
    const { data } = await api.patch(`/pedidos/${id}/estado`, { estado: nuevoEstado });
    return data;
  },

  // 👇 4. REEMPLAZAMOS LOS 'any' CON NUESTRAS INTERFACES
  crear: async (payload: CrearPedidoPayload): Promise<Pedido> => {
    const { data } = await api.post('/pedidos/', payload);
    return data; // Generalmente el backend devuelve el pedido creado
  }
};