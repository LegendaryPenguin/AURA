import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiClientError, postAnalyze } from '../../../client/src/services/api';
import type { AnalysisRequest } from '../../../client/src/types/overlay';

const validRequest: AnalysisRequest = {
  request_id: 'req-1',
  session_id: 'session-1',
  image_base64: 'ZmFrZQ==',
  query: 'what is this',
  capture_ts_ms: 1700000000000,
};

describe('api response validation', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('accepts schema-valid analyze response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        request_id: 'req-1',
        session_id: 'session-1',
        created_at: '2026-01-01T00:00:00Z',
        overlays: [
          {
            bbox: { x: 0.1, y: 0.2, width: 0.2, height: 0.3 },
            label: 'widget',
            confidence: 0.9,
            ui_layer: 'foreground',
            overlay_type: 'info',
            action_required: false,
          },
        ],
      }),
    } as Response);

    const response = await postAnalyze(validRequest);
    expect(response.request_id).toBe('req-1');
    expect(response.overlays).toHaveLength(1);
  });

  it('rejects out-of-range bbox/invalid enum values', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        request_id: 'req-1',
        session_id: 'session-1',
        created_at: '2026-01-01T00:00:00Z',
        overlays: [
          {
            bbox: { x: 2, y: 0.2, width: 0.2, height: 0.3 },
            label: 'widget',
            confidence: 0.9,
            ui_layer: 'bogus',
            overlay_type: 'bad',
            action_required: false,
          },
        ],
      }),
    } as Response);

    await expect(postAnalyze(validRequest)).rejects.toBeInstanceOf(ApiClientError);
  });

  it('rejects invalid created_at', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        request_id: 'req-1',
        session_id: 'session-1',
        created_at: 'not-a-date',
        overlays: [],
      }),
    } as Response);

    await expect(postAnalyze(validRequest)).rejects.toBeInstanceOf(ApiClientError);
  });
});
