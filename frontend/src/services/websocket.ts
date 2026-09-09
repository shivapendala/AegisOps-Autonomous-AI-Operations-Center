/**
 * WebSocket client for AegisOps Real-Time Monitor.
 */
import { ConnectionState, WebSocketEvent } from '../types';

export type MessageCallback = (event: WebSocketEvent) => void;
export type StateCallback = (state: ConnectionState, reconnectDelayMs?: number) => void;

export class MonitoringSocket {
  private socket: WebSocket | null = null;
  private url: string;
  private onMessage: MessageCallback;
  private onStateChange: StateCallback;
  private reconnectTimeout: number | null = null;
  private pingInterval: number | null = null;
  private reconnectAttempts = 0;
  private isExplicitlyClosed = false;
  private maxReconnectDelay = 10000; // max 10s backoff

  constructor(
    url: string = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/monitor',
    onMessage: MessageCallback,
    onStateChange: StateCallback
  ) {
    this.url = url;
    this.onMessage = onMessage;
    this.onStateChange = onStateChange;
  }

  public connect(): void {
    this.isExplicitlyClosed = false;
    this.clearTimers();

    const state: ConnectionState = this.reconnectAttempts > 0 ? 'reconnecting' : 'connecting';
    this.onStateChange(state);

    try {
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        this.reconnectAttempts = 0;
        this.onStateChange('connected');
        this.startPingKeepalive();
      };

      this.socket.onmessage = (event: MessageEvent) => {
        try {
          const parsed: WebSocketEvent = JSON.parse(event.data);
          this.onMessage(parsed);
        } catch {
          // Non-JSON message, ignore
        }
      };

      this.socket.onerror = () => {
        // Handled in onclose
      };

      this.socket.onclose = () => {
        this.stopPingKeepalive();
        if (!this.isExplicitlyClosed) {
          this.onStateChange('disconnected');
          this.scheduleReconnect();
        } else {
          this.onStateChange('disconnected');
        }
      };
    } catch {
      this.onStateChange('disconnected');
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout || this.isExplicitlyClosed) return;

    this.reconnectAttempts += 1;
    // Exponential backoff: 1s, 2s, 4s, 8s, up to 10s
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), this.maxReconnectDelay);

    this.onStateChange('reconnecting', delay);

    this.reconnectTimeout = window.setTimeout(() => {
      this.reconnectTimeout = null;
      this.connect();
    }, delay);
  }

  private startPingKeepalive(): void {
    this.stopPingKeepalive();
    // Send ping keepalive every 15 seconds
    this.pingInterval = window.setInterval(() => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send('ping');
      }
    }, 15000);
  }

  private stopPingKeepalive(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private clearTimers(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    this.stopPingKeepalive();
  }

  public disconnect(): void {
    this.isExplicitlyClosed = true;
    this.clearTimers();
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.onStateChange('disconnected');
  }
}
