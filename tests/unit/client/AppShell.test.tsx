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

// Avoid pulling the full overlay canvas + RLE path graph during transform (prevents OOM in Vitest).
vi.mock('../../../client/src/components/overlays/OverlayCanvas', () => ({
  default: function MockOverlayCanvas() {
    return <div data-testid="mock-overlay-canvas" />;
  },
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

  it('renders video stage with overlay canvas', async () => {
    render(<App />);
    await waitFor(() => expect(getUserMediaMock).toHaveBeenCalled());

    expect(screen.getByText('AURA App Shell')).toBeInTheDocument();
    const video = document.querySelector('video');
    const canvas = document.querySelector('canvas');
    expect(video).toBeTruthy();
    expect(canvas).toBeTruthy();
  });

  it('phase selector updates mode label', async () => {
    render(<App />);
    await waitFor(() => expect(getUserMediaMock).toHaveBeenCalled());
    const select = screen.getByLabelText('Phase');

    fireEvent.change(select, { target: { value: '4' } });

    await waitFor(() => {
      expect(screen.getByText('Mode: Tracked AR')).toBeInTheDocument();
    });
  });

  it('phase 0 shows static demo overlay without calling analyze API', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    render(<App />);
    await waitFor(() => expect(getUserMediaMock).toHaveBeenCalled());
    const select = screen.getByLabelText('Phase');

    fireEvent.change(select, { target: { value: '0' } });
    const analyzeButton = screen.getByRole('button', { name: 'Capture + Analyze' });
    expect(analyzeButton).toBeDisabled();

    await waitFor(() => {
      expect(screen.getByText('Mode: Fallback')).toBeInTheDocument();
      expect(screen.getByText('Overlay count: 1')).toBeInTheDocument();
    });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('non-fallback analyze posts to API and uses response overlays', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => validOverlayResponse,
    } as Response);

    render(<App />);
    await waitFor(() => expect(getUserMediaMock).toHaveBeenCalled());
    fireEvent.click(screen.getByRole('button', { name: 'Capture + Analyze' }));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalled();
      const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit];
      expect(call[0]).toBe('/analyze');
      expect(call[1]?.method).toBe('POST');
      expect(screen.getByText('Overlay count: 1')).toBeInTheDocument();
    });
  });
});
