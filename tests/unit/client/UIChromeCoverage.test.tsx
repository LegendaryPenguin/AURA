import { act, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { AgentActionToast } from '../../../client/src/components/agents/AgentActionToast';
import { DepthHeatmap } from '../../../client/src/components/ui/DepthHeatmap';
import { FallbackVideo } from '../../../client/src/components/ui/FallbackVideo';
import { ScanReticle } from '../../../client/src/components/ui/ScanReticle';

describe('WS2-E UI chrome coverage', () => {
  it('renders fallback video container when mounted', () => {
    Object.defineProperty(HTMLMediaElement.prototype, 'play', {
      configurable: true,
      value: vi.fn().mockResolvedValue(undefined),
    });
    Object.defineProperty(HTMLMediaElement.prototype, 'pause', {
      configurable: true,
      value: vi.fn(),
    });

    render(<FallbackVideo src="demo.mp4" isPlaying onEnded={vi.fn()} onTimeUpdate={vi.fn()} />);
    expect(screen.getByTestId('fallback-video')).toBeInTheDocument();
  });

  it('renders scan reticle only when visible', () => {
    const { rerender } = render(<ScanReticle visible={false} />);
    expect(screen.queryByTestId('scan-reticle')).toBeNull();
    rerender(<ScanReticle visible size={160} />);
    expect(screen.getByTestId('scan-reticle')).toBeInTheDocument();
  });

  it('renders and auto-dismisses agent toast', () => {
    vi.useFakeTimers();
    const onDismiss = vi.fn();
    render(
      <AgentActionToast
        message="Agent started analysis"
        type="triggered"
        visible
        autoDismissMs={500}
        onDismiss={onDismiss}
      />,
    );
    expect(screen.getByTestId('agent-toast')).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(onDismiss).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it('renders depth heatmap and paints canvas data', () => {
    const putImageData = vi.fn();
    Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
      configurable: true,
      value: vi.fn(() => ({
        createImageData: (width: number, height: number) => ({ data: new Uint8ClampedArray(width * height * 4) }),
        putImageData,
      })),
    });

    render(
      <DepthHeatmap
        depthMap={new Float32Array([0.1, 0.3, 0.6, 1.0])}
        width={2}
        height={2}
      />,
    );
    expect(screen.getByTestId('depth-heatmap')).toBeInTheDocument();
    expect(putImageData).toHaveBeenCalledTimes(1);
  });
});
