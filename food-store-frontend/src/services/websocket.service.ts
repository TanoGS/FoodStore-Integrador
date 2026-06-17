// ─────────────────────────────────────────────────────────────────────
// WebSocketService — singleton que maneja UNA conexión WS por tab.
//
// Diseño: cada tab abre SU PROPIO WebSocket con SU PROPIO token.
// Esto permite tener N pestañas abiertas con N usuarios distintos
// (o repetidos) sin que se pisen entre sí. El backend rutea los
// eventos a las salas correctas (user:{id} y/o staff:pedidos)
// y cada tab recibe los suyos.
//
// Antes este servicio tenía "leader election" (1 WS por origin),
// lo cual era correcto para 1 usuario en varias tabs pero rompía
// el caso multi-user-multi-tab. Se removió la lógica de líder y
// el BroadcastChannel asociado — cada tab es independiente.
// ─────────────────────────────────────────────────────────────────────

import { useWSStore, type EstadoWS, type WSEvent, type StockAlerta } from '../store/wsStore';
import { fallbackPolling } from './fallbackPolling.service';

// ─── Constantes ─────────────────────────────────────────────────────

const WS_PATH                    = '/api/ws/pedidos';
const HEARTBEAT_INTERVAL_MS      = 25_000;   // ping cada 25s
const PONG_TIMEOUT_MS            = 60_000;   // si no hay pong en 60s, reconecta
const RECONNECT_DELAYS_MS        = [1_000, 2_000, 4_000, 8_000, 16_000, 30_000];

// ─── Tipos internos ────────────────────────────────────────────────

type Subscriber = (ev: WSEvent) => void;

// ─── Clase ──────────────────────────────────────────────────────────

class WebSocketService {
  // ── Estado interno ──
  private socket:                WebSocket | null = null;
  private token:                 string | null = null;
  private isDisconnecting        = false;     // para no reconectar en logout
  private heartbeatInterval:     ReturnType<typeof setInterval> | null = null;
  private pongTimeout:           ReturnType<typeof setTimeout>  | null = null;
  private reconnectTimeout:      ReturnType<typeof setTimeout>  | null = null;
  private retryCount             = 0;
  private authErrorCallback:     (() => void) | null = null;

  // ── Subscribers a eventos ──
  private subscribers: Set<Subscriber> = new Set();

  // ── Singleton ──
  private static _instance: WebSocketService;
  static getInstance(): WebSocketService {
    if (!WebSocketService._instance) {
      WebSocketService._instance = new WebSocketService();
    }
    return WebSocketService._instance;
  }

  private constructor() {
    // El WS se abre recién cuando se llama a connect(token).
    // Cada tab es completamente independiente: sin líder, sin
    // BroadcastChannel, sin storage compartido.
  }

  // ──────────────────────────────────────────────────────────────────
  // API pública
  // ──────────────────────────────────────────────────────────────────

  /**
   * Llamar cuando el usuario se loguea. Pasa el JWT y se abre
   * la conexión WS de esta tab.
   */
  connect(token: string): void {
    this.token = token;
    this.isDisconnecting = false;
    this.openSocket();
  }

  /**
   * Llamar cuando el usuario se desloguea. Cierra el WS.
   */
  disconnect(): void {
    this.isDisconnecting = true;
    this.token = null;
    this.clearReconnect();
    this.closeSocket();
    this.stopHeartbeat();
    this.setEstado('closed');
  }

  /**
   * Suscribe un handler a TODOS los eventos que llegan por el WS.
   * Devuelve una función de cleanup.
   */
  subscribe(handler: Subscriber): () => void {
    this.subscribers.add(handler);
    return () => { this.subscribers.delete(handler); };
  }

  /**
   * Registra un callback que se invoca cuando el WS detecta un error
   * de autenticación (token inválido o expirado, código 1008).
   * Lo usa el authStore para forzar logout.
   */
  onAuthError(cb: () => void): void {
    this.authErrorCallback = cb;
  }

  // ──────────────────────────────────────────────────────────────────
  // Conexión WS
  // ──────────────────────────────────────────────────────────────────

  private openSocket(): void {
    if (!this.token) return;
    if (this.socket &&
        (this.socket.readyState === WebSocket.OPEN ||
         this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }
    this.isDisconnecting = false;
    this.setEstado('connecting');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // En dev, VITE_WS_URL (de .env.development) permite conectar DIRECTO
    // al backend (puerto 8000) y evitar problemas con el upgrade de
    // WebSocket a través del proxy de Vite.
    // En prod se deja vacía y se usa window.location.host (reverse proxy).
    const envBase  = (import.meta.env.VITE_WS_URL ?? '').replace(/\/+$/, '');
    const host     = envBase || `${protocol}//${window.location.host}`;
    const url      = `${host}${WS_PATH}?token=${encodeURIComponent(this.token)}`;

    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch (err) {
      console.error('[WS] No se pudo crear el WebSocket:', err);
      this.scheduleReconnect();
      return;
    }
    this.socket = ws;
    ws.addEventListener('open',    this.onSocketOpen);
    ws.addEventListener('message', this.onSocketMessage);
    ws.addEventListener('error',   this.onSocketError);
    ws.addEventListener('close',   this.onSocketClose);
  }

  private closeSocket(): void {
    if (!this.socket) return;
    this.socket.removeEventListener('open',    this.onSocketOpen);
    this.socket.removeEventListener('message', this.onSocketMessage);
    this.socket.removeEventListener('error',   this.onSocketError);
    this.socket.removeEventListener('close',   this.onSocketClose);
    try { this.socket.close(1000, 'Logout'); } catch { /* noop */ }
    this.socket = null;
  }

  private onSocketOpen = (): void => {
    this.retryCount = 0;
    this.setEstado('open');
    this.startHeartbeat();
  };

  private onSocketMessage = (ev: MessageEvent): void => {
    let data: WSEvent;
    try {
      data = JSON.parse(ev.data) as WSEvent;
    } catch {
      console.warn('[WS] Mensaje no es JSON válido:', ev.data);
      return;
    }

    if (data.type === 'pong') {
      this.handlePong();
      return;
    }
    if (data.type === 'hello') {
      // Mensaje de bienvenida del servidor, nada que hacer
      return;
    }

    // Despachar a subscribers locales + store
    this.dispatchEvent(data);
  };

  private onSocketError = (_ev: Event): void => {
    console.error('[WS] Error en el WebSocket');
    this.setEstado('error');
  };

  private onSocketClose = (ev: CloseEvent): void => {
    this.stopHeartbeat();
    this.clearPongTimeout();

    // Auth error → forzar logout
    if (ev.code === 1008 && ev.reason && /[Tt]oken/.test(ev.reason)) {
      console.warn('[WS] Token inválido o expirado, forzando logout');
      this.authErrorCallback?.();
      this.setEstado('error');
      return;
    }

    if (this.isDisconnecting) {
      this.setEstado('closed');
      return;
    }

    // Caída inesperada: programar reconexión
    this.scheduleReconnect();
  };

  // ──────────────────────────────────────────────────────────────────
  // Reconexión con backoff
  // ──────────────────────────────────────────────────────────────────

  private scheduleReconnect(): void {
    if (this.reconnectTimeout) return;
    if (!this.token) return;

    const baseDelay = RECONNECT_DELAYS_MS[
      Math.min(this.retryCount, RECONNECT_DELAYS_MS.length - 1)
    ];
    const jitter   = baseDelay * 0.2 * (Math.random() * 2 - 1);  // ±20%
    const finalMs  = Math.max(500, Math.floor(baseDelay + jitter));

    this.retryCount += 1;
    this.setEstado('reconnecting');

    this.reconnectTimeout = setTimeout(() => {
      this.reconnectTimeout = null;
      this.openSocket();
    }, finalMs);
  }

  private clearReconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    this.retryCount = 0;
  }

  // ──────────────────────────────────────────────────────────────────
  // Heartbeat (ping)
  // ──────────────────────────────────────────────────────────────────

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => this.sendPing(), HEARTBEAT_INTERVAL_MS);
    // Ping inicial para empezar el ciclo
    this.sendPing();
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    this.clearPongTimeout();
  }

  private sendPing(): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
    try {
      this.socket.send(JSON.stringify({ type: 'ping' }));
    } catch (err) {
      console.warn('[WS] No se pudo enviar ping:', err);
    }
    this.schedulePongTimeout();
  }

  private schedulePongTimeout(): void {
    this.clearPongTimeout();
    this.pongTimeout = setTimeout(() => {
      console.warn('[WS] Pong timeout, forzando reconexión');
      if (this.socket) {
        try { this.socket.close(4000, 'Pong timeout'); } catch { /* noop */ }
      }
    }, PONG_TIMEOUT_MS);
  }

  private handlePong(): void {
    this.clearPongTimeout();
  }

  private clearPongTimeout(): void {
    if (this.pongTimeout) {
      clearTimeout(this.pongTimeout);
      this.pongTimeout = null;
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // Despacho de eventos
  // ──────────────────────────────────────────────────────────────────

  private dispatchEvent(ev: WSEvent): void {
    // Subscribers locales
    this.subscribers.forEach((h) => {
      try { h(ev); }
      catch (err) { console.error('[WS] Error en subscriber:', err); }
    });
    // Store (ring buffer + estado)
    useWSStore.getState().pushEvento(ev);

    // Si es alerta de stock, guardarla en la cola del store
    if (ev.type === 'stock.alerta') {
      useWSStore.getState().pushStockAlerta(ev.payload as StockAlerta);
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // Helpers de estado / store
  // ──────────────────────────────────────────────────────────────────

  private setEstado(estado: EstadoWS): void {
    useWSStore.getState().setEstado(estado);

    // ─── Fallback REST con polling (metodología PDF, paso 4) ───
    // - 'open'                → WS sano → detener polling
    // - 'reconnecting'/'error' → WS caído  → activar polling
    // - 'closed' (logout)     → apagar polling también
    if (estado === 'open' || estado === 'closed' || estado === 'idle') {
      fallbackPolling.stop();
    } else if (estado === 'reconnecting' || estado === 'error') {
      fallbackPolling.start();
    }
  }
}

// Singleton exportado
export const wsService = WebSocketService.getInstance();
