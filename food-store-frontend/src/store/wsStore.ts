import { create } from 'zustand';

// ─────────────────────────────────────────────────────────────────────
// Tipos públicos de eventos que el backend puede emitir.
// (Mirror de foood-store-backend/app/modules/pedido/events.py)
// ─────────────────────────────────────────────────────────────────────

export interface WSEvent {
  type:    string;
  payload: unknown;
  ts?:     number;
}

export type EstadoWS =
  | 'idle'         // Aún no se intentó conectar
  | 'connecting'   // El líder está abriendo el WebSocket
  | 'open'         // El WebSocket del líder está abierto
  | 'reconnecting' // El WebSocket se cayó; el líder reintenta con backoff
  | 'closed'       // Cierre limpio (logout)
  | 'error';       // Error de conexión o token inválido

// ─────────────────────────────────────────────────────────────────────
// Store de Zustand. Es el ÚNICO punto de verdad que el front lee.
// El servicio (websocket.service.ts) lo actualiza vía getState().
// ─────────────────────────────────────────────────────────────────────

interface WSState {
  estado:      EstadoWS;
  ultimoError: string | null;
  // Ring buffer de los últimos N eventos. Útil para depurar en DevTools
  // y para que un componente que se monta tarde pueda ver eventos recientes.
  eventos:     WSEvent[];

  setEstado:    (estado: EstadoWS) => void;
  setError:     (msg: string | null) => void;
  pushEvento:   (event: WSEvent) => void;
  clearEventos: () => void;
}

const BUFFER_SIZE = 50;

export const useWSStore = create<WSState>((set) => ({
  estado:      'idle',
  ultimoError: null,
  eventos:     [],

  setEstado: (estado) => set({ estado }),
  setError:  (msg)    => set({ ultimoError: msg }),
  pushEvento: (event) => set((state) => {
    const eventos = [event, ...state.eventos];
    if (eventos.length > BUFFER_SIZE) {
      eventos.length = BUFFER_SIZE;
    }
    return { eventos };
  }),
  clearEventos: () => set({ eventos: [] }),
}));
