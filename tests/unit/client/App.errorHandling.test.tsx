import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  runAnalysis: vi.fn(),
  clearOverlays: vi.fn(),
  hydrateFromResponse: vi.fn(),
  replaceOverlays: vi.fn(),
  captureFrame: vi.fn(),
  getHealth: vi.fn(),
}));

vi.mock("../../../client/src/hooks/useOverlay", () => ({
  useOverlay: () => ({
    overlays: [],
    clearOverlays: mocks.clearOverlays,
    hydrateFromResponse: mocks.hydrateFromResponse,
    replaceOverlays: mocks.replaceOverlays,
  }),
}));

vi.mock("../../../client/src/hooks/useSnapshotAnalysis", () => ({
  useSnapshotAnalysis: () => ({
    runAnalysis: mocks.runAnalysis,
    isLoading: false,
    error: null,
    status: "idle",
  }),
}));

vi.mock("../../../client/src/hooks/useFrameCapture", () => ({
  useFrameCapture: () => ({
    captureFrame: mocks.captureFrame,
  }),
}));

vi.mock("../../../client/src/hooks/useFallback", () => ({
  useFallback: () => ({
    fallbackData: null,
    isFallbackActive: false,
    clearFallback: vi.fn(),
  }),
}));

vi.mock("../../../client/src/services/api", async () => {
  const actual = await vi.importActual("../../../client/src/services/api");
  return {
    ...actual,
    getHealth: mocks.getHealth,
    getBackendTarget: () => ({ mode: "real", baseUrl: "" }),
  };
});

vi.mock("../../../client/src/components/overlays/OverlayCanvas", () => ({
  default: () => <div data-testid="overlay-canvas" />,
}));

vi.mock("../../../client/src/components/ui/ScanAnimation", () => ({
  ScanAnimation: () => <div />,
}));

vi.mock("../../../client/src/components/ui/ScanReticle", () => ({
  ScanReticle: () => <div />,
}));

vi.mock("../../../client/src/components/ui/DepthHeatmap", () => ({
  DepthHeatmap: () => <div />,
}));

vi.mock("../../../client/src/components/ui/FallbackVideo", () => ({
  FallbackVideo: () => <div />,
}));

vi.mock("../../../client/src/components/ui/ConfidenceIndicator", () => ({
  ConfidenceIndicator: () => <div />,
}));

vi.mock("../../../client/src/components/agents/AgentActionToast", () => ({
  AgentActionToast: () => <div />,
}));

import App from "../../../client/src/App";

describe("App analyze failure handling", () => {
  beforeEach(() => {
    mocks.runAnalysis.mockReset();
    mocks.clearOverlays.mockReset();
    mocks.hydrateFromResponse.mockReset();
    mocks.replaceOverlays.mockReset();
    mocks.captureFrame.mockReset();
    mocks.getHealth.mockReset();
    mocks.getHealth.mockResolvedValue({ status: "healthy", models: { vlm: "ready" } });
    mocks.runAnalysis.mockRejectedValue(new Error("request failed"));
    Object.defineProperty(HTMLMediaElement.prototype, "pause", {
      configurable: true,
      value: vi.fn(),
    });
    Object.defineProperty(HTMLMediaElement.prototype, "play", {
      configurable: true,
      value: vi.fn().mockResolvedValue(undefined),
    });
  });

  it("preserves existing overlays after analyze failure", async () => {
    render(<App />);
    fireEvent.click(screen.getByLabelText("Capture and analyze"));
    await waitFor(() => {
      expect(screen.getByText(/Error: request failed/i)).toBeInTheDocument();
    });
    expect(mocks.clearOverlays).not.toHaveBeenCalled();
  });
});
