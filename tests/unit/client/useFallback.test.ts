import { renderHook, act } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { useFallback, FALLBACK_PAYLOAD } from '../../../client/src/hooks/useFallback';

describe('useFallback', () => {
  it('returns null fallback data initially', () => {
    const { result } = renderHook(() => useFallback());

    expect(result.current.fallbackData).toBeNull();
    expect(result.current.isFallbackActive).toBe(false);
  });

  it('triggerFallback sets fallback data and activates', () => {
    const { result } = renderHook(() => useFallback());

    act(() => {
      result.current.triggerFallback();
    });

    expect(result.current.fallbackData).not.toBeNull();
    expect(result.current.isFallbackActive).toBe(true);
  });

  it('fallback payload contains overlays matching schema shape', () => {
    const { result } = renderHook(() => useFallback());

    act(() => {
      result.current.triggerFallback();
    });

    const data = result.current.fallbackData!;
    expect(data.overlays).toBeInstanceOf(Array);
    expect(data.overlays.length).toBeGreaterThan(0);
    expect(data.timestamp).toBeTypeOf('number');
    expect(data.session_id).toBeTypeOf('string');

    for (const overlay of data.overlays) {
      expect(overlay.bbox).toHaveLength(4);
      overlay.bbox.forEach((v) => {
        expect(v).toBeGreaterThanOrEqual(0);
        expect(v).toBeLessThanOrEqual(1);
      });
      expect(overlay.label).toBeTypeOf('string');
      expect(overlay.confidence).toBeGreaterThanOrEqual(0);
      expect(overlay.confidence).toBeLessThanOrEqual(1);
      expect(['diagnostic', 'hazard', 'info', 'reference']).toContain(overlay.overlay_type);
      expect(overlay.ui_layer).toBeTypeOf('number');
      expect(overlay.action_required).toBeTypeOf('boolean');
    }
  });

  it('hardcoded payload covers multiple overlay types', () => {
    const types = FALLBACK_PAYLOAD.overlays.map((o) => o.overlay_type);
    expect(types).toContain('diagnostic');
    expect(types).toContain('hazard');
    expect(types).toContain('info');
  });

  it('clearFallback resets state', () => {
    const { result } = renderHook(() => useFallback());

    act(() => {
      result.current.triggerFallback();
    });
    expect(result.current.isFallbackActive).toBe(true);

    act(() => {
      result.current.clearFallback();
    });
    expect(result.current.fallbackData).toBeNull();
    expect(result.current.isFallbackActive).toBe(false);
  });

  it('Shift+F keydown triggers fallback', () => {
    const { result } = renderHook(() => useFallback());

    act(() => {
      window.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'F', shiftKey: true }),
      );
    });

    expect(result.current.fallbackData).not.toBeNull();
    expect(result.current.isFallbackActive).toBe(true);
  });

  it('non-Shift+F keys do not trigger fallback', () => {
    const { result } = renderHook(() => useFallback());

    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'F', shiftKey: false }));
    });
    expect(result.current.fallbackData).toBeNull();

    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'G', shiftKey: true }));
    });
    expect(result.current.fallbackData).toBeNull();
  });
});
