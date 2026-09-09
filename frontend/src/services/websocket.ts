import { WebSocketTelemetryMessage } from '../types';

export type MessageCallback = (data: WebSocketTelemetryMessage) => void;
export type StatusCallback = (connected: boolean) => void;

export class TelemetrySocket {
  private socket: WebSocket | null = null;
  private url: string;
  private onMessage: MessageCallback;
  private onStatus: StatusCallback;
  private reconnectTimeout: number | null = null;
  private isExplicitlyClosed = false;

  constructor(
    url: string = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/telemetry',
    onMessage: MessageCallback,
    onStatus: StatusCallback
  ) {
    this.url = url;
    this.onMessage = onMessage;
    this.onStatus = onStatus;
  }

  public connect(): void {
    this.isExplicitlyClosed = false;
    try {
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        this.onStatus(true);
      };

      this.socket.onmessage = (event: MessageEvent) => {
        try {
          const parsed: WebSocketTelemetryMessage = JSON.parse(event.data);
          this.onMessage(parsed);
        } catch {
          // Ignore non-JSON ping/pong strings
        }
      };

      this.socket.onerror = () => {
        this.onStatus(false);
      };

      this.socket.onclose = () => {
        this.onStatus(false);
        if (!this.isExplicitlyClosed) {
          this.scheduleReconnect();
        }
      };
    } catch {
      this.onStatus(false);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout) return;
    this.reconnectTimeout = window.setTimeout(() => {
      this.reconnectTimeout = null;
      this.connect();
    }, 3000);
  }

  public disconnect(): void {
    this.isExplicitlyClosed = true;
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.onStatus(false);
  }
}
