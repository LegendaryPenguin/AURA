import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useOverlay } from "../../../client/src/hooks/useOverlay";

function makeDraft(id?: string) {
  return {
    id,
    overlay_type: "diagnostic" as const,
    ui_layer: "foreground" as const,
    label: "Unit under test",
    confidence: 0.88,
    action_required: false,
    bbox: { x: 0.2, y: 0.3, width: 0.2, height: 0.2 },
  };
}

describe("useOverlay hook lifecycle", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it("handles entering -> visible -> exiting -> removed lifecycle", () => {
    const { result } = renderHook(() => useOverlay({ autoDismissMs: 100, exitAnimationMs: 20 }));

    let id = "";
    act(() => {
      id = result.current.addOverlay(makeDraft("overlay-1"));
    });
    expect(id).toBe("overlay-1");
    expect(result.current.overlays).toHaveLength(1);
    expect(result.current.overlays[0]?.animationState).toBe("entering");

    act(() => {
      vi.advanceTimersByTime(24);
    });
    expect(result.current.overlays[0]?.animationState).toBe("visible");

    act(() => {
      vi.advanceTimersByTime(76);
    });
    expect(result.current.overlays[0]?.animationState).toBe("exiting");

    act(() => {
      vi.advanceTimersByTime(20);
    });
    expect(result.current.overlays).toHaveLength(0);
  });

  it("supports multiple overlays plus explicit remove/clear", () => {
    const { result } = renderHook(() => useOverlay({ autoDismissMs: 500, exitAnimationMs: 50 }));

    let ids: string[] = [];
    act(() => {
      ids = result.current.addOverlays([makeDraft("a"), makeDraft("b")]);
    });
    expect(ids).toEqual(["a", "b"]);
    expect(result.current.overlays).toHaveLength(2);

    act(() => {
      result.current.removeOverlay("a");
      vi.advanceTimersByTime(50);
    });
    expect(result.current.overlays.map((item) => item.id)).toEqual(["b"]);

    act(() => {
      result.current.clearOverlays();
    });
    expect(result.current.overlays).toHaveLength(0);
  });
});
