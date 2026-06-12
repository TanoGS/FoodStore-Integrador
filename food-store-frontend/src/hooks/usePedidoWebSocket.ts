import { useEffect } from 'react';
import { wsService } from '../services/websocket.service';
import { useWSStore, type WSEvent } from '../store/wsStore';

// ─────────────────────────────────────────────────────────────────────
// usePedidoWebSocket
// Hook liviano: lee el estado de la conexión y permite suscribirse
// a eventos con un callback. La conexión se maneja en
// authStore.ts (en setLogin / logout); este hook NO la abre.
// ─────────────────────────────────────────────────────────────────────

export function usePedidoWebSocket() {
  const estado      = useWSStore((s) => s.estado);
  const ultimoError = useWSStore((s) => s.ultimoError);

  return { estado, ultimoError };
}

/**
 * Suscribe un handler a los eventos del WS. El handler se llama en
 * cada evento (venga del WS o re-emitido por el líder vía BroadcastChannel).
 *
 *   usePedidoEventos((ev) => {
 *     if (ev.type === 'pedido.creado') { ... }
 *   });
 */
export function usePedidoEventos(handler: (ev: WSEvent) => void): void {
  useEffect(() => {
    const unsub = wsService.subscribe(handler);
    return unsub;
    // handler puede ser una función nueva en cada render; confiamos en
    // que el caller la estabilice con useCallback si lo necesita.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [handler]);
}
