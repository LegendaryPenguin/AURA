import { useCallback, useEffect, useRef, useState } from "react";

export interface UseAutoScanOptions {
  intervalMs?: number;
  onScan: () => Promise<void>;
  enabled: boolean;
}

export interface UseAutoScanReturn {
  isAutoScanning: boolean;
  toggleAutoScan: () => void;
  scanCount: number;
  lastScanTs: number | null;
  lastError: string | null;
}

export function useAutoScan(options: UseAutoScanOptions): UseAutoScanReturn {
  const { intervalMs = 2500, onScan, enabled } = options;
  const [isAutoScanning, setIsAutoScanning] = useState(false);
  const [scanCount, setScanCount] = useState(0);
  const [lastScanTs, setLastScanTs] = useState<number | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const scanningRef = useRef(false);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const runScan = useCallback(async () => {
    if (scanningRef.current) return;
    scanningRef.current = true;
    setLastError(null);

    try {
      await onScan();
      setScanCount((c) => c + 1);
      setLastScanTs(Date.now());
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Scan failed";
      setLastError(msg);
    } finally {
      scanningRef.current = false;
    }
  }, [onScan]);

  const toggleAutoScan = useCallback(() => {
    setIsAutoScanning((prev) => !prev);
  }, []);

  useEffect(() => {
    if (!enabled) {
      setIsAutoScanning(false);
    }
  }, [enabled]);

  useEffect(() => {
    clearTimer();
    if (!isAutoScanning || !enabled) return;

    void runScan();
    timerRef.current = setInterval(() => {
      void runScan();
    }, intervalMs);

    return clearTimer;
  }, [isAutoScanning, enabled, intervalMs, runScan, clearTimer]);

  return { isAutoScanning, toggleAutoScan, scanCount, lastScanTs, lastError };
}
