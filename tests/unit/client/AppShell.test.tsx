import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../../client/src/hooks/useFrameCapture', () => ({
  useFrameCapture: () => ({
    captureFrame: () => ({
      dataUrl:
        'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAn/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBEQCEAD8All//Z',
      width: 8,
      height: 8,
    }),
  }),
}));

vi.mock('../../../client/src/components/overlays/OverlayCanvas', () => ({
  default: function MockOverlayCanvas() {
    return <div data-testid="mock-overlay-canvas" />;
  },
}));

vi.mock('../../../client/src/components/ui/StatusBar', () => ({
  StatusBar: function MockStatusBar() {
    return <div data-testid="mock-status-bar" />;
  },
}));

vi.mock('../../../client/src/components/ui/ScanAnimation', () => ({
  ScanAnimation: function MockScanAnimation() {
    return null;
  },
}));

vi.mock('../../../client/src/hooks/useCamera', () => ({
  useCamera: () => ({
    videoRef: { current: null },
    isReady: true,
    error: null,
    start: vi.fn(),
    stop: vi.fn(),
    switchFacing: vi.fn(),
    facing: 'environment',
  }),
}));

vi.mock('../../../client/src/hooks/useAudioRecorder', () => ({
  useAudioRecorder: () => ({
    isRecording: false,
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
    holdToRecord: vi.fn(),
    error: null,
  }),
}));

import App from '../../../client/src/App';

const getUserMediaMock = vi.fn();
const playMock = vi.fn(async () => undefined);
const pauseMock = vi.fn();
const stopTrackMock = vi.fn();
const fillRectMock = vi.fn();
const clearRectMock = vi.fn();
const strokeRectMock = vi.fn();
const fillTextMock = vi.fn();
const measureTextMock = vi.fn(() => ({ width: 42 }));
const setTransformMock = vi.fn();
const getBoundingClientRectMock = vi.fn(() => ({ width: 800, height: 450, top: 0, left: 0 }));

const validOverlayResponse = {
  request_id: 'req-1',
  session_id: 's-1',
  created_at: '2020-01-01T00:00:00+00:00',
  model_version: 'test',
  overlays: [
    {
      bbox: { x: 0.1, y: 0.1, width: 0.2, height: 0.2 },
      label: 'Mock result',
      confidence: 0.88,
      ui_layer: 'foreground' as const,
      overlay_type: 'info' as const,
      action_required: false,
    },
  ],
};

function mockCanvas2d() {
  return {
    clearRect: clearRectMock,
    strokeRect: strokeRectMock,
    fillRect: fillRectMock,
    fillText: fillTextMock,
    measureText: measureTextMock,
    setTransform: setTransformMock,
    drawImage: vi.fn(),
    putImageData: vi.fn(),
    getImageData: vi.fn(),
    set lineWidth(_value: number) {},
    set font(_value: string) {},
    set textBaseline(_value: CanvasTextBaseline) {},
    set strokeStyle(_value: string) {},
    set fillStyle(_value: string) {},
  };
}

describe('App shell integration', () => {
  beforeEach(() => {
    getUserMediaMock.mockResolvedValue({
      getTracks: () => [{ stop: stopTrackMock }],
    });

    Object.defineProperty(global.navigator, 'mediaDevices', {
      value: { getUserMedia: getUserMediaMock },
      configurable: true,
    });

    Object.defineProperty(HTMLMediaElement.prototype, 'play', {
      value: playMock,
      configurable: true,
    });
    Object.defineProperty(HTMLMediaElement.prototype, 'pause', {
      value: pauseMock,
      configurable: true,
    });
    Object.defineProperty(HTMLMediaElement.prototype, 'videoWidth', {
      get: () => 960,
      configurable: true,
    });
    Object.defineProperty(HTMLMediaElement.prototype, 'videoHeight', {
      get: () => 540,
      configurable: true,
    });
    Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
      value: vi.fn(() => mockCanvas2d()),
      configurable: true,
    });
    Object.defineProperty(HTMLCanvasElement.prototype, 'getBoundingClientRect', {
      value: getBoundingClientRectMock,
      configurable: true,
    });

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'healthy', models: {} }),
    } as Response);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    getUserMediaMock.mockReset();
    playMock.mockClear();
    pauseMock.mockClear();
    stopTrackMock.mockClear();
    fillRectMock.mockClear();
    clearRectMock.mockClear();
    strokeRectMock.mockClear();
    fillTextMock.mockClear();
    measureTextMock.mockClear();
    setTransformMock.mockClear();
  });

  it('renders title and overlay canvas', () => {
    render(<App />);
    expect(screen.getByText('AURA')).toBeInTheDocument();
    expect(screen.getByTestId('mock-overlay-canvas')).toBeInTheDocument();
  });

  it('phase selector updates mode label in footer', async () => {
    render(<App />);
    const select = screen.getByLabelText('Phase');

    fireEvent.change(select, { target: { value: '2' } });

    await waitFor(() => {
      expect(screen.getByText('Mode: Live Camera + Voice')).toBeInTheDocument();
    });
  });

  it('phase 0 shows Fallback mode', async () => {
    render(<App />);
    const select = screen.getByLabelText('Phase');

    fireEvent.change(select, { target: { value: '0' } });

    await waitFor(() => {
      expect(screen.getByText('Mode: Fallback')).toBeInTheDocument();
    });
  });

  it('phase 3 shows auto-scan button', async () => {
    render(<App />);
    const select = screen.getByLabelText('Phase');

    fireEvent.change(select, { target: { value: '3' } });

    await waitFor(() => {
      expect(screen.getByText('Start Auto-Scan')).toBeInTheDocument();
    });
  });

  it('phase 1 shows Capture + Analyze button', () => {
    render(<App />);
    expect(screen.getByText('Capture + Analyze')).toBeInTheDocument();
  });

  it('non-fallback analyze posts to API and uses response overlays', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => validOverlayResponse,
    } as Response);

    render(<App />);
    fireEvent.click(screen.getByText('Capture + Analyze'));

    await waitFor(() => {
      const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls;
      const analyzeCalls = calls.filter((c: unknown[]) => String(c[0]).includes('/analyze'));
      expect(analyzeCalls.length).toBeGreaterThanOrEqual(1);
    });
  });
});
