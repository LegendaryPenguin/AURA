import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { OverlayItem, OverlayResponse } from "../types/overlay";

export type OverlayAnimationState = "entering" | "visible" | "exiting";
export type OverlaySeverity = "low" | "medium" | "high" | "critical";
export type OverlayDraft = OverlayItem & { id?: string; severity?: OverlaySeverity };

export interface OverlayStateItem extends OverlayDraft {
  id: string;
  createdAt: number;
  dismissAt: number;
  animationState: OverlayAnimationState;
}

export interface UseOverlayOptions {
  autoDismissMs?: number;
  exitAnimationMs?: number;
}

export interface UseOverlayReturn {
  overlays: OverlayStateItem[];
  addOverlay: (overlay: OverlayDraft) => string;
  addOverlays: (items: OverlayDraft[]) => string[];
  replaceOverlays: (items: OverlayDraft[]) => string[];
  removeOverlay: (id: string) => void;
  clearOverlays: () => void;
  hydrateFromResponse: (response: OverlayResponse) => string[];
}

const DEFAULT_AUTO_DISMISS_MS = 8000;
const DEFAULT_EXIT_ANIMATION_MS = 220;
const ENTER_TO_VISIBLE_MS = 24;
const UI_LAYER_ORDER: Record<OverlayItem["ui_layer"], number> = {
  background: 0,
  midground: 1,
  foreground: 2,
  hud: 3,
};

export function useOverlay(options: UseOverlayOptions = {}): UseOverlayReturn {
  const autoDismissMs = options.autoDismissMs ?? DEFAULT_AUTO_DISMISS_MS;
  const exitAnimationMs = options.exitAnimationMs ?? DEFAULT_EXIT_ANIMATION_MS;
  const [overlays, setOverlays] = useState<OverlayStateItem[]>([]);
  const timersRef = useRef<Map<string, number[]>>(new Map());

  const clearTimersFor = useCallback((id: string) => {
    const handles = timersRef.current.get(id);
    if (!handles) {
      return;
    }
    handles.forEach((handle) => window.clearTimeout(handle));
    timersRef.current.delete(id);
  }, []);

  const scheduleLifecycle = useCallback(
    (id: string) => {
      const toVisible = window.setTimeout(() => {
        setOverlays((current) =>
          current.map((item) =>
            item.id === id && item.animationState === "entering"
              ? { ...item, animationState: "visible" }
              : item,
          ),
        );
      }, ENTER_TO_VISIBLE_MS);

      const dismiss = window.setTimeout(() => {
        setOverlays((current) =>
          current.map((item) =>
            item.id === id && item.animationState !== "exiting"
              ? { ...item, animationState: "exiting" }
              : item,
          ),
        );
      }, autoDismissMs);

      const cleanup = window.setTimeout(() => {
        setOverlays((current) => current.filter((item) => item.id !== id));
        clearTimersFor(id);
      }, autoDismissMs + exitAnimationMs);

      timersRef.current.set(id, [toVisible, dismiss, cleanup]);
    },
    [autoDismissMs, clearTimersFor, exitAnimationMs],
  );

  const createOverlayState = useCallback(
    (overlay: OverlayDraft): OverlayStateItem => {
      const now = Date.now();
      const id = overlay.id ?? `overlay-${now}-${Math.random().toString(16).slice(2, 8)}`;
      return {
        ...overlay,
        id,
        createdAt: now,
        dismissAt: now + autoDismissMs,
        animationState: "entering",
      };
    },
    [autoDismissMs],
  );

  const addOverlay = useCallback(
    (overlay: OverlayDraft): string => {
      const next = createOverlayState(overlay);
      setOverlays((current) =>
        [...current, next].sort((a, b) => UI_LAYER_ORDER[a.ui_layer] - UI_LAYER_ORDER[b.ui_layer]),
      );
      scheduleLifecycle(next.id);
      return next.id;
    },
    [createOverlayState, scheduleLifecycle],
  );

  const addOverlays = useCallback(
    (items: OverlayDraft[]): string[] => items.map((item) => addOverlay(item)),
    [addOverlay],
  );

  const removeOverlay = useCallback(
    (id: string) => {
      clearTimersFor(id);
      setOverlays((current) =>
        current.map((item) =>
          item.id === id ? { ...item, animationState: "exiting" } : item,
        ),
      );
      const removal = window.setTimeout(() => {
        setOverlays((current) => current.filter((item) => item.id !== id));
        clearTimersFor(id);
      }, exitAnimationMs);
      timersRef.current.set(id, [removal]);
    },
    [clearTimersFor, exitAnimationMs],
  );

  const clearOverlays = useCallback(() => {
    timersRef.current.forEach((handles) => handles.forEach((handle) => window.clearTimeout(handle)));
    timersRef.current.clear();
    setOverlays([]);
  }, []);

  const replaceOverlays = useCallback(
    (items: OverlayDraft[]): string[] => {
      clearOverlays();
      return items.map((item) => addOverlay(item));
    },
    [addOverlay, clearOverlays],
  );

  const hydrateFromResponse = useCallback(
    (response: OverlayResponse): string[] => replaceOverlays(response.overlays),
    [replaceOverlays],
  );

  useEffect(() => () => clearOverlays(), [clearOverlays]);

  const value = useMemo<UseOverlayReturn>(
    () => ({
      overlays,
      addOverlay,
      addOverlays,
      replaceOverlays,
      removeOverlay,
      clearOverlays,
      hydrateFromResponse,
    }),
    [addOverlay, addOverlays, clearOverlays, hydrateFromResponse, overlays, removeOverlay, replaceOverlays],
  );

  return value;
}
