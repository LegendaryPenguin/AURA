import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { ApiClientError, postAnalyze } from "../../../client/src/services/api";
import { useSnapshotAnalysis } from "../../../client/src/hooks/useSnapshotAnalysis";
import type { OverlayResponse } from "../../../client/src/types/overlay";

vi.mock("../../../client/src/services/api", async () => {
  const actual = await vi.importActual("../../../client/src/services/api");
  return {
    ...actual,
    postAnalyze: vi.fn(),
  };
});

const mockedPostAnalyze = vi.mocked(postAnalyze);

const successResponse: OverlayResponse = {
  request_id: "req-1",
  session_id: "session-1",
  created_at: "2026-01-01T00:00:00Z",
  overlays: [],
};

describe("useSnapshotAnalysis", () => {
  beforeEach(() => {
    mockedPostAnalyze.mockReset();
  });

  it("transitions idle -> loading -> success", async () => {
    const captureFrame = vi.fn().mockResolvedValue("ZmFrZQ==");
    mockedPostAnalyze.mockResolvedValue(successResponse);

    const { result } = renderHook(() => useSnapshotAnalysis({ captureFrame }));
    expect(result.current.status).toBe("idle");

    let pending: Promise<OverlayResponse>;
    act(() => {
      pending = result.current.runAnalysis({
        sessionId: "session-1",
        query: "What is this?",
      });
    });
    expect(result.current.status).toBe("loading");

    await act(async () => {
      await pending!;
    });

    expect(result.current.status).toBe("success");
    expect(result.current.data?.request_id).toBe("req-1");
    expect(result.current.error).toBeNull();
  });

  it("transitions idle -> loading -> error", async () => {
    const captureFrame = vi.fn().mockResolvedValue("ZmFrZQ==");
    const timeoutError = new ApiClientError(
      "The server timed out processing this snapshot. Please try again.",
      "REQUEST_TIMEOUT",
      408,
    );
    mockedPostAnalyze.mockRejectedValue(timeoutError);

    const { result } = renderHook(() => useSnapshotAnalysis({ captureFrame }));
    expect(result.current.status).toBe("idle");

    let pending: Promise<OverlayResponse>;
    act(() => {
      pending = result.current.runAnalysis({
        sessionId: "session-1",
        query: "What is this?",
      });
    });
    expect(result.current.status).toBe("loading");

    await act(async () => {
      await expect(pending!).rejects.toBeInstanceOf(ApiClientError);
    });

    expect(result.current.status).toBe("error");
    expect(result.current.data).toBeNull();
    expect(result.current.errorCode).toBe("REQUEST_TIMEOUT");
    expect(result.current.error).toContain("timed out");
  });
});
