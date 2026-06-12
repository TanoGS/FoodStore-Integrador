// ─────────────────────────────────────────────────────────────────────
// FallbackPollingService — singleton de respaldo REST.
//
// Metodología "WebSockets con JWT en FastAPI" (Unidad 5), sección
// "Estrategia de Fallback (REST de Respaldo)":
//
//   "El frontend debe implementar una lógica de resiliencia: si el
//    WebSocket se desconecta, cambiar temporalmente a polling REST
//    hasta restablecer la conexión."
//
//   - ws.onclose → activa modo fallback
//   - GET /pedidos/?… cada 5-10s
//   - al volver a 'open' → detener polling
//
// Decisiones de diseño:
//   - Arranca tras un pequeño delay (ACTIVATION_DELAY_MS) para no
//     competir con los reintentos rápidos del WS (1s, 2s, 4s...).
//   - Es idempotente: start()/stop() pueden llamarse N veces.
//   - Emite los resultados al mismo useWSStore que el WS, con un
//     evento sintético `polling.actualizado` para que la UI lo pueda
//     distinguir si lo necesita.
//   - Usa la instancia `api` (no axios crudo) para reusar el
//     interceptor de Authorization y la cookie HttpOnly del login.
// ─────────────────────────────────────────────────────────────────────

import api from '../config/axios';
import { useWSStore, type WSEvent } from '../store/wsStore';

// Endpoint: GET /pedidos/?offset=0&limit=50
// (definido en foood-store-backend/app/modules/pedido/router.py).
// Path RELATIVO al baseURL de `api` (http://127.0.0.1:8000/api) —
// axios no debe duplicar el prefijo.
// Traemos los últimos 50 pedidos sin filtro de estado, así el polling
// sirve tanto para la vista de staff (todos) como para la del cliente
// (el backend ya filtra por usuario en el service).
const POLL_MS               = 7_000;     // 7s entre polls (rango recomendado: 5-10s)
const ACTIVATION_DELAY_MS   = 4_000;     // espera antes de activar el primer poll
const POLLING_PATH          = '/pedidos/?offset=0&limit=50';

class FallbackPollingService {
  private pollInterval:        ReturnType<typeof setInterval> | null = null;
  private activationTimeout:   ReturnType<typeof setTimeout>  | null = null;
  private isRunning            = false;
  private lastSnapshotKey      = '';     // hash simple para no emitir si no hubo cambios
  private pollInFlight         = false;  // evita requests superpuestas

  private static _instance: FallbackPollingService;
  static getInstance(): FallbackPollingService {
    if (!FallbackPollingService._instance) {
      FallbackPollingService._instance = new FallbackPollingService();
    }
    return FallbackPollingService._instance;
  }

  /**
   * Arranca el polling si no estaba corriendo. Si el WS vuelve antes
   * de ACTIVATION_DELAY_MS, stop() cancela el primer poll.
   */
  start(): void {
    if (this.isRunning) return;
    this.isRunning = true;

    // Marcamos en el store que estamos en modo fallback
    useWSStore.getState().setEstado('reconnecting');

    // Primer poll con delay
    this.activationTimeout = setTimeout(() => {
      this.activationTimeout = null;
      if (!this.isRunning) return;     // se canceló antes de tiempo
      void this.pollOnce();
      this.pollInterval = setInterval(() => void this.pollOnce(), POLL_MS);
    }, ACTIVATION_DELAY_MS);

    // eslint-disable-next-line no-console
    console.info('[FallbackPolling] activado (primer poll en', ACTIVATION_DELAY_MS, 'ms)');
  }

  /**
   * Detiene el polling. Idempotente.
   */
  stop(): void {
    if (!this.isRunning) return;
    this.isRunning = false;

    if (this.activationTimeout) {
      clearTimeout(this.activationTimeout);
      this.activationTimeout = null;
    }
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
    this.lastSnapshotKey = '';

    // eslint-disable-next-line no-console
    console.info('[FallbackPolling] desactivado (WS recuperado)');
  }

  /**
   * ¿Está activo? Útil para debugging o para que la UI muestre un badge.
   */
  isActive(): boolean {
    return this.isRunning;
  }

  // ─── interno ───────────────────────────────────────────────────────

  private async pollOnce(): Promise<void> {
    // Guarda: si hay un poll en curso, salteamos este tick para no
    // apilar requests cuando el backend está lento.
    if (this.pollInFlight) return;
    this.pollInFlight = true;

    try {
      // Usamos `api` (no axios crudo) para que el interceptor de
      // Authorization se aplique y se mande la cookie HttpOnly.
      const { data } = await api.get<unknown[]>(POLLING_PATH, {
        timeout: 5_000,
      });

      // Hash simple: si el payload no cambió, no emitimos
      const key = JSON.stringify(data);
      if (key === this.lastSnapshotKey) return;
      this.lastSnapshotKey = key;

      const ev: WSEvent = {
        type:    'polling.actualizado',
        payload: { pedidos: data, source: 'fallback-polling' },
        ts:      Date.now(),
      };
      useWSStore.getState().pushEvento(ev);
    } catch (err) {
      // Si el polling también falla, lo logueamos pero NO levantamos
      // una excepción: la idea es ser resiliente, no romperse más.
      // eslint-disable-next-line no-console
      console.warn('[FallbackPolling] error en poll:', err);
    } finally {
      this.pollInFlight = false;
    }
  }
}

export const fallbackPolling = FallbackPollingService.getInstance();
