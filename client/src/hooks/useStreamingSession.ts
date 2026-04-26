import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useWebSocket } from "./useWebSocket";

export interface UseStreamingSessionReturn {
  enabled: boolean;
  isConnected: boolean;
  lastOverlay: unknown;
  start: () => void;
  stop: () => void;
  pushFrame: (frame: Uint8Array) => void;
}

export function useStreamingSession(
  wsUrl: string,
  maxFps = 15,
): UseStreamingSessionReturn {
  const [enabled, setEnabled] = useState(false);
  const lastSentRef = useRef(0);
  const { isConnected, lastMessage, sendBinary, close } = useWebSocket(wsUrl, enabled);
  const minInterval = 1000 / maxFps;

  const pushFrame = useCallback(
    (frame: Uint8Array) => {
      const now = performance.now();
      if (now - lastSentRef.current < minInterval) {
        return;
      }
      lastSentRef.current = now;
      sendBinary(frame);
    },
    [minInterval, sendBinary],
  );

  useEffect(() => {
    if (!enabled) {
      close();
    }
  }, [close, enabled]);

  return useMemo(
    () => ({
      enabled,
      isConnected,
      lastOverlay: lastMessage,
      start: () => setEnabled(true),
      stop: () => setEnabled(false),
      pushFrame,
    }),
    [enabled, isConnected, lastMessage, pushFrame],
  );
}
