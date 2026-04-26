import { useEffect, useMemo, useState } from "react";

import { ReconnectingSocket } from "../services/socket";

export interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: unknown;
  sendBinary: (frame: Uint8Array) => void;
  close: () => void;
}

export function useWebSocket(url: string, enabled: boolean): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<unknown>(null);
  const [client, setClient] = useState<ReconnectingSocket | null>(null);

  useEffect(() => {
    if (!enabled) {
      client?.close();
      setClient(null);
      setIsConnected(false);
      return;
    }
    const socket = new ReconnectingSocket(url, {
      onOpen: () => setIsConnected(true),
      onClose: () => setIsConnected(false),
      onMessage: (payload) => setLastMessage(payload),
    });
    socket.connect();
    setClient(socket);
    return () => socket.close();
  }, [enabled, url]);

  return useMemo(
    () => ({
      isConnected,
      lastMessage,
      sendBinary: (frame: Uint8Array) => client?.sendBinary(frame),
      close: () => client?.close(),
    }),
    [client, isConnected, lastMessage],
  );
}
