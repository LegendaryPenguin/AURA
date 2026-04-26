import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import type { OverlayStateItem } from "../../hooks/useOverlay";
import { decodeRle } from "./MaskOverlay";

interface OverlayCanvasProps {
  overlays: OverlayStateItem[];
  className?: string;
  style?: CSSProperties;
}

const UI_LAYER_ORDER: Record<OverlayStateItem["ui_layer"], number> = {
  background: 0,
  midground: 1,
  foreground: 2,
  hud: 3,
};

function toCanvasRect(
  bbox: OverlayStateItem["bbox"],
  width: number,
  height: number,
): { x: number; y: number; w: number; h: number } {
  return {
    x: bbox.x * width,
    y: bbox.y * height,
    w: bbox.width * width,
    h: bbox.height * height,
  };
}

function drawMaskInsideBoundingBox(
  ctx: CanvasRenderingContext2D,
  overlay: OverlayStateItem,
  canvasWidth: number,
  canvasHeight: number,
): void {
  if (!overlay.mask_rle) {
    return;
  }

  const decoded = decodeRle(overlay.mask_rle);
  if (!decoded) {
    return;
  }

  const raw = decoded.counts;
  const mask = new Uint8Array(decoded.width * decoded.height);
  let write = 0;
  let active = false;
  raw.forEach((count) => {
    for (let i = 0; i < count && write < mask.length; i += 1) {
      mask[write] = active ? 1 : 0;
      write += 1;
    }
    active = !active;
  });

  const image = new ImageData(decoded.width, decoded.height);
  for (let i = 0; i < mask.length; i += 1) {
    if (!mask[i]) {
      continue;
    }
    const base = i * 4;
    image.data[base] = 16;
    image.data[base + 1] = 185;
    image.data[base + 2] = 129;
    image.data[base + 3] = 70;
  }

  const offscreen = document.createElement("canvas");
  offscreen.width = decoded.width;
  offscreen.height = decoded.height;
  const offscreenCtx = offscreen.getContext("2d");
  if (!offscreenCtx) {
    return;
  }
  offscreenCtx.putImageData(image, 0, 0);

  const rect = toCanvasRect(overlay.bbox, canvasWidth, canvasHeight);
  ctx.drawImage(offscreen, rect.x, rect.y, rect.w, rect.h);
}

export default function OverlayCanvas({ overlays, className, style }: OverlayCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [containerSize, setContainerSize] = useState({ w: 0, h: 0 });

  useEffect(() => {
    const parent = canvasRef.current?.parentElement;
    if (!parent) return;
    const observer = new ResizeObserver(([entry]) => {
      if (!entry) return;
      const { width, height } = entry.contentRect;
      setContainerSize({ w: width, h: height });
    });
    observer.observe(parent);
    return () => observer.disconnect();
  }, []);

  const sortedOverlays = useMemo(
    () => [...overlays].sort((a, b) => UI_LAYER_ORDER[a.ui_layer] - UI_LAYER_ORDER[b.ui_layer]),
    [overlays],
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }

    const deviceRatio = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.floor(rect.width * deviceRatio));
    canvas.height = Math.max(1, Math.floor(rect.height * deviceRatio));
    ctx.setTransform(deviceRatio, 0, 0, deviceRatio, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);
    ctx.lineWidth = 2;
    ctx.font = "12px Inter, system-ui, sans-serif";
    ctx.textBaseline = "top";

    sortedOverlays.forEach((overlay) => {
      const { x, y, w, h } = toCanvasRect(overlay.bbox, rect.width, rect.height);
      const tone =
        overlay.overlay_type === "hazard"
          ? { stroke: "#f43f5e", fill: "rgba(244, 63, 94, 0.18)" }
          : overlay.overlay_type === "diagnostic"
            ? { stroke: "#3b82f6", fill: "rgba(59, 130, 246, 0.18)" }
            : { stroke: "#94a3b8", fill: "rgba(148, 163, 184, 0.14)" };

      drawMaskInsideBoundingBox(ctx, overlay, rect.width, rect.height);

      ctx.strokeStyle = tone.stroke;
      ctx.fillStyle = tone.fill;
      ctx.strokeRect(x, y, w, h);
      ctx.fillRect(x, y, w, h);

      const label = `${overlay.label} ${(overlay.confidence * 100).toFixed(0)}%`;
      const labelWidth = ctx.measureText(label).width + 12;
      const labelY = Math.max(0, y - 20);
      ctx.fillStyle = "rgba(2, 6, 23, 0.86)";
      ctx.fillRect(x, labelY, labelWidth, 18);
      ctx.fillStyle = "#e2e8f0";
      ctx.fillText(label, x + 6, labelY + 3);
    });
  }, [sortedOverlays, containerSize]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
        zIndex: 6,
        ...style,
      }}
    />
  );
}
