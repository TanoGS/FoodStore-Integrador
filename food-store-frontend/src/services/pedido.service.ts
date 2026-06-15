import api from '../config/axios';


// ─────────────────────────────────────────────────────────────────────
// Direcciones resumidas (eco del schema DireccionResumida del backend)
// ─────────────────────────────────────────────────────────────────────
export interface DireccionResumida {
  calle:      string | null;
  numero:     string | null;
  ciudad:     string | null;
  referencia: string | null;
}


// ─────────────────────────────────────────────────────────────────────
// PedidoAdmin — enriquecido para vistas de staff (GestorPedidos)
// Eco del schema PedidoAdmin del backend.
// ─────────────────────────────────────────────────────────────────────
export interface PedidoAdmin {
  id:                 number;
  usuario_id:         number;
  usuario_nombre:      string;
  usuario_email:      string;
  direccion_id:       number | null;
  direccion:          DireccionResumida | null;
  estado_codigo:      string;
  forma_pago_codigo:  string;
  forma_pago_label:   string;
  tipo_entrega:       string;   // 'EN_LOCAL' | 'DELIVERY'
  tipo_entrega_label: string;   // 'En el local' | 'Delivery'
  subtotal:          number;
  descuento:          number;
  costo_envio:        number;
  total:             number;
  notas:             string | null;
  creado_en:         string;
  detalles:          DetallePedidoPublic[];
}

// Detalle individual dentro de un pedido
export interface DetallePedidoPublic {
  producto_id:           number;
  cantidad:              number;
  nombre_snapshot:       string;
  precio_snapshot:       number;
  subtotal_snap:        number;
  personalizacion?:       number[];       // IDs de ingredientes removidos
  personalizacion_nombres?: string[];    // Nombres para mostrar
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
  producto_id:     number;
  cantidad:        number;
  personalizacion?: number[] | null;
}

// Molde exacto del payload de creación
// Campo "detalles" = mirror del schema PedidoCreate del backend
// (foood-store-backend/app/modules/pedido/schemas.py:23)
export type TipoEntrega = 'EN_LOCAL' | 'DELIVERY';

export const TIPO_ENTREGA_LABELS: Record<TipoEntrega, string> = {
  EN_LOCAL: 'En el local',
  DELIVERY: 'Delivery',
};

export interface CrearPedidoPayload {
  direccion_id:       number | null;
  forma_pago_codigo:  'EFECTIVO' | 'MERCADOPAGO';
  tipo_entrega:       TipoEntrega;
  notas?:              string | null;
  detalles:            PedidoItemPayload[];
}

// ─────────────────────────────────────────────────────────────────────
// FSM mirror del backend
// (foood-store-backend/app/modules/pedido/service.py:_FSM)
// Si se modifica la máquina de estados en el backend, reflejar acá.
// ─────────────────────────────────────────────────────────────────────
export const ESTADOS_FSM: Record<string, string[]> = {
  PENDIENTE:      ['CONFIRMADO',     'CANCELADO'],
  CONFIRMADO:     ['EN_PREPARACION', 'CANCELADO'],
  EN_PREPARACION: ['EN_CAMINO',      'CANCELADO'],
  EN_CAMINO:      ['ENTREGADO'],
  ENTREGADO:      [],
  CANCELADO:      [],
};

// Estados terminales (no se puede cambiar desde acá)
export const ESTADOS_TERMINALES: readonly string[] = ['ENTREGADO', 'CANCELADO'];

// Códigos de los roles de staff que pueden operar pedidos en el backend
// (alineado con foood-store-backend/app/modules/pedido/router.py:RoleChecker)
export const ROLES_STAFF_PEDIDOS: readonly string[] = [
  'ADMIN',
  'GESTOR_PEDIDOS',
  'COCINA',
];

// Helper para normalizar la respuesta (algunas rutas devuelven array
// directo, otras { data, total } paginado)
function normalizarLista(raw: unknown): PedidoPublic[] {
  if (Array.isArray(raw)) return raw as PedidoPublic[];
  if (raw && typeof raw === 'object' && Array.isArray((raw as { data?: unknown }).data)) {
    return (raw as { data: PedidoPublic[] }).data;
  }
  return [];
}

// Helper para normalizar la respuesta de PedidoAdmin (respuesta paginada)
function normalizarListaAdmin(raw: unknown): PedidoAdmin[] {
  if (Array.isArray(raw)) return raw as PedidoAdmin[];
  if (raw && typeof raw === 'object' && Array.isArray((raw as { data?: unknown }).data)) {
    return (raw as { data: PedidoAdmin[] }).data;
  }
  return [];
}

export const PedidoService = {
  // Admin/Gestor: trae todos. Cliente: solo los suyos. El backend filtra por rol.
  listarTodos: async (): Promise<PedidoPublic[]> => {
    const { data } = await api.get('/pedidos/');
    return normalizarLista(data);
  },

  // Alias semántico para la pantalla del cliente (llama al mismo endpoint)
  listarMisPedidos: async (params?: {
    offset?: number;
    limit?: number;
  }): Promise<{ data: PedidoPublic[]; total: number }> => {
    const { offset = 0, limit = 10 } = params ?? {};
    const { data } = await api.get('/pedidos/', { params: { offset, limit } });
    // El backend devuelve { data: [...], total: N }
    if (Array.isArray(data)) {
      return { data: data as PedidoPublic[], total: (data as PedidoPublic[]).length };
    }
    return data as { data: PedidoPublic[]; total: number };
  },

  // Endpoint enriquecido para GestorPedidos (staff). Trae datos expandidos
  // de cliente, dirección y forma de pago + filtro de período.
  listarTodosAdmin: async (
    periodo?: 'DIARIO' | 'MENSUAL',
  ): Promise<PedidoAdmin[]> => {
    const params = periodo ? `?periodo=${periodo}` : '';
    const { data } = await api.get(`/pedidos/admin${params}`);
    return normalizarListaAdmin(data);
  },

  // Cambia el estado del pedido.
  // El backend exige el campo `estado_hacia` y un `motivo` obligatorio
  // cuando el destino es CANCELADO (AvanzarEstadoRequest en schemas.py).
  actualizarEstado: async (
    id: number,
    nuevoEstado: string,
    motivo?: string
  ): Promise<PedidoPublic> => {
    const body: { estado_hacia: string; motivo?: string } = {
      estado_hacia: nuevoEstado,
    };
    if (motivo && motivo.trim().length > 0) {
      body.motivo = motivo.trim();
    }
    const { data } = await api.patch(`/pedidos/${id}/estado`, body);
    return data as PedidoPublic;
  },

  crear: async (payload: CrearPedidoPayload): Promise<PedidoPublic> => {
    const { data } = await api.post('/pedidos/', payload);
    return data as PedidoPublic;
  },
};
