import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DiagnosticCard from "../../../client/src/components/overlays/DiagnosticCard";
import HazardWarning from "../../../client/src/components/overlays/HazardWarning";
import InfoBox from "../../../client/src/components/overlays/InfoBox";
import OverlayCanvas from "../../../client/src/components/overlays/OverlayCanvas";
import { drawRleMaskToCanvas } from "../../../client/src/components/overlays/MaskOverlay";
import type { OverlayStateItem } from "../../../client/src/hooks/useOverlay";

function makeOverlay(overrides: Partial<OverlayStateItem> = {}): OverlayStateItem {
  return {
    id: "ov-1",
    createdAt: Date.now(),
    dismissAt: Date.now() + 8000,
    animationState: "visible",
    overlay_type: "diagnostic",
    ui_layer: "foreground",
    label: "Breaker panel",
    confidence: 0.9,
    action_required: false,
    bbox: { x: 0.1, y: 0.2, width: 0.3, height: 0.4 },
    ...overrides,
  };
}

describe("WS2-D overlay rendering", () => {
  it("renders diagnostic card at expected normalized position", () => {
    const overlay = makeOverlay();
    const { container } = render(<DiagnosticCard overlay={overlay} />);
    const article = container.querySelector("article");
    expect(article).toBeTruthy();
    expect(article?.style.left).toBe("10%");
    expect(article?.style.top).toBe("8%");
    expect(article?.style.width).toBe("30%");
    expect(article?.style.border).toContain("59, 130, 246");
  });

  it("renders hazard and info overlays with expected color treatments", () => {
    const hazard = makeOverlay({ overlay_type: "hazard", severity: "critical" });
    const info = makeOverlay({ id: "ov-2", overlay_type: "info" });

    const { container: hazardContainer, getByText: getHazardText } = render(<HazardWarning overlay={hazard} />);
    const { container: infoContainer, getByText: getInfoText } = render(<InfoBox overlay={info} />);

    expect(getHazardText("Hazard Warning")).toBeTruthy();
    expect(getInfoText("Info")).toBeTruthy();

    const hazardArticle = hazardContainer.querySelector("article");
    const infoAside = infoContainer.querySelector("aside");
    expect(hazardArticle?.style.border).toContain("248, 113, 113");
    expect(infoAside?.style.border).toContain("148, 163, 184");
  });
});

describe("WS2-D overlay canvas", () => {
  const strokeRect = vi.fn();
  const fillRect = vi.fn();
  const fillText = vi.fn();
  const drawImage = vi.fn();
  const putImageData = vi.fn();
  const clearRect = vi.fn();
  const setTransform = vi.fn();

  beforeEach(() => {
    vi.spyOn(window, "devicePixelRatio", "get").mockReturnValue(1);
    vi.spyOn(HTMLCanvasElement.prototype, "getBoundingClientRect").mockReturnValue({
      width: 200,
      height: 100,
      x: 0,
      y: 0,
      top: 0,
      left: 0,
      right: 200,
      bottom: 100,
      toJSON: () => ({}),
    });
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(() => {
      return {
        strokeRect,
        fillRect,
        fillText,
        drawImage,
        clearRect,
        setTransform,
        measureText: () => ({ width: 50 }),
        createImageData: (w: number, h: number) => ({
          data: new Uint8ClampedArray(w * h * 4),
          width: w,
          height: h,
          colorSpace: "srgb",
        }),
        putImageData,
      } as unknown as CanvasRenderingContext2D;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    strokeRect.mockReset();
    fillRect.mockReset();
    fillText.mockReset();
    drawImage.mockReset();
    putImageData.mockReset();
    clearRect.mockReset();
    setTransform.mockReset();
  });

  it("maps overlay bbox to expected pixel coordinates on canvas", () => {
    const overlay = makeOverlay();
    render(<OverlayCanvas overlays={[overlay]} />);
    expect(strokeRect).toHaveBeenCalledWith(20, 20, 60, 40);
    expect(fillRect).toHaveBeenCalledWith(20, 20, 60, 40);
  });

  it("renders multiple overlays in same frame without dropping either", () => {
    const overlayA = makeOverlay({ id: "ov-a", bbox: { x: 0.1, y: 0.1, width: 0.1, height: 0.1 } });
    const overlayB = makeOverlay({
      id: "ov-b",
      overlay_type: "hazard",
      bbox: { x: 0.6, y: 0.4, width: 0.2, height: 0.2 },
    });
    render(<OverlayCanvas overlays={[overlayA, overlayB]} />);
    expect(strokeRect).toHaveBeenCalledTimes(2);
  });

  it("draws decoded RLE mask to canvas image buffer", () => {
    const canvas = document.createElement("canvas");
    canvas.width = 4;
    canvas.height = 4;

    drawRleMaskToCanvas({
      canvas,
      maskRle: "4 4|4 4 8",
    });

    expect(putImageData).toHaveBeenCalled();
    const imageData = putImageData.mock.calls[0]?.[0] as ImageData;
    const alphaValues: number[] = [];
    for (let i = 3; i < imageData.data.length; i += 4) {
      alphaValues.push(imageData.data[i]);
    }
    expect(alphaValues.some((value) => value > 0)).toBe(true);
  });
});
