export type SocketEventHandlers = {
  onOpen?: () => void;
  onClose?: () => void;
  onMessage?: (payload: unknown) => void;
  onError?: (error: Event) => void;
};

export class ReconnectingSocket {
  private socket: WebSocket | null = null;

  private retries = 0;

  private closedByUser = false;

  constructor(
    private readonly url: string,
    private readonly handlers: SocketEventHandlers = {},
  ) {}

  connect(): void {
    this.closedByUser = false;
    this.socket = new WebSocket(this.url);
    this.socket.binaryType = "arraybuffer";
    this.socket.onopen = () => {
      this.retries = 0;
      this.handlers.onOpen?.();
    };
    this.socket.onmessage = (event) => {
      try {
        this.handlers.onMessage?.(JSON.parse(String(event.data)));
      } catch {
        this.handlers.onMessage?.(event.data);
      }
    };
    this.socket.onerror = (event) => this.handlers.onError?.(event);
    this.socket.onclose = () => {
      this.handlers.onClose?.();
      if (!this.closedByUser) {
        const delay = Math.min(1000 * 2 ** this.retries, 10_000);
        this.retries += 1;
        window.setTimeout(() => this.connect(), delay);
      }
    };
  }

  sendBinary(frame: Uint8Array): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(frame);
    }
  }

  close(): void {
    this.closedByUser = true;
    this.socket?.close(1000, "client-close");
    this.socket = null;
  }
}
