import { useState, useEffect, useCallback, useMemo } from 'react';

export type OverlayType = 'diagnostic' | 'hazard' | 'info' | 'reference';

export interface OverlayItem {
  bbox: [number, number, number, number];
  label: string;
  confidence: number;
  ui_layer: number;
  overlay_type: OverlayType;
  action_required: boolean;
  mask_rle?: string;
  depth_value?: number;
}

export interface OverlayResponse {
  overlays: OverlayItem[];
  timestamp: number;
  session_id: string;
}

const FALLBACK_PAYLOAD: OverlayResponse = {
  overlays: [
    {
      bbox: [0.12, 0.15, 0.55, 0.60],
      label: 'Overheating component detected',
      confidence: 0.92,
      ui_layer: 1,
      overlay_type: 'diagnostic',
      action_required: true,
    },
    {
      bbox: [0.60, 0.10, 0.90, 0.45],
      label: 'Exposed wiring — shock risk',
      confidence: 0.87,
      ui_layer: 2,
      overlay_type: 'hazard',
      action_required: true,
    },
    {
      bbox: [0.05, 0.70, 0.40, 0.95],
      label: 'Model: XR-500 Rev C',
      confidence: 0.78,
      ui_layer: 0,
      overlay_type: 'info',
      action_required: false,
    },
  ],
  timestamp: Date.now(),
  session_id: 'fallback-session',
};

export interface UseFallbackReturn {
  fallbackData: OverlayResponse | null;
  isFallbackActive: boolean;
  triggerFallback: () => void;
  clearFallback: () => void;
}

export function useFallback(): UseFallbackReturn {
  const [fallbackData, setFallbackData] = useState<OverlayResponse | null>(null);
  const [isFallbackActive, setIsFallbackActive] = useState(false);

  const triggerFallback = useCallback(() => {
    const payload: OverlayResponse = {
      ...FALLBACK_PAYLOAD,
      timestamp: Date.now(),
    };
    setFallbackData(payload);
    setIsFallbackActive(true);
  }, []);

  const clearFallback = useCallback(() => {
    setFallbackData(null);
    setIsFallbackActive(false);
  }, []);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.shiftKey && e.key === 'F') {
        triggerFallback();
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [triggerFallback]);

  return useMemo(() => ({
    fallbackData, isFallbackActive, triggerFallback, clearFallback,
  }), [fallbackData, isFallbackActive, triggerFallback, clearFallback]);
}

export { FALLBACK_PAYLOAD };
