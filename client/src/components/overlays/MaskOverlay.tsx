import { useEffect, useRef } from "react";

export interface RleMask {
  width: number;
  height: number;
  counts: number[];
}

export interface DrawMaskOptions {
  canvas: HTMLCanvasElement;
  maskRle: string;
  color?: [number, number, number];
  opacity?: number;
  contourColor?: [number, number, number];
  contourAlpha?: number;
}

interface MaskOverlayProps {
  maskRle: string;
  className?: string;
  opacity?: number;
}

const DEFAULT_FILL: [number, number, number] = [16, 185, 129];
const DEFAULT_CONTOUR: [number, number, number] = [5, 150, 105];

export function decodeRle(maskRle: string): RleMask | null {
  if (!maskRle) {
    return null;
  }

  const normalized = maskRle.trim();

  if (normalized.startsWith("{")) {
    try {
      const parsed = JSON.parse(normalized) as { size?: [number, number]; counts?: number[] | string };
      if (!parsed.size?.length || !parsed.counts) {
        return null;
      }
      const [height, width] = parsed.size;
      const counts =
        typeof parsed.counts === "string"
          ? parsed.counts
              .split(/[,\s]+/)
              .filter(Boolean)
              .map((value) => Number(value))
          : parsed.counts;
      return { width, height, counts };
    } catch {
      return null;
    }
  }

  // Supported compact format: "width height|0 12 4 6 ..."
  const [sizeRaw, countsRaw] = normalized.split("|");
  if (!countsRaw) {
    return null;
  }

  const [width, height] = sizeRaw
    .split(/[x,\s]+/)
    .map((token) => Number(token))
    .filter((token) => Number.isFinite(token) && token > 0);
  if (!width || !height) {
    return null;
  }

  const counts = countsRaw
    .split(/[,\s]+/)
    .filter(Boolean)
    .map((token) => Number(token))
    .filter((token) => Number.isFinite(token) && token >= 0);

  if (!counts.length) {
    return null;
  }

  return { width, height, counts };
}

function expandMask(rle: RleMask): Uint8Array {
  const totalPixels = rle.width * rle.height;
  const output = new Uint8Array(totalPixels);
  let writeIndex = 0;
  let isMask = false;

  rle.counts.forEach((runLength) => {
    const length = Math.max(0, Math.floor(runLength));
    for (let i = 0; i < length && writeIndex < totalPixels; i += 1) {
      output[writeIndex] = isMask ? 1 : 0;
      writeIndex += 1;
    }
    isMask = !isMask;
  });

  return output;
}

function isEdgePixel(mask: Uint8Array, width: number, height: number, x: number, y: number): boolean {
  const index = y * width + x;
  if (!mask[index]) {
    return false;
  }
  const left = x > 0 ? mask[index - 1] : 0;
  const right = x < width - 1 ? mask[index + 1] : 0;
  const top = y > 0 ? mask[index - width] : 0;
  const bottom = y < height - 1 ? mask[index + width] : 0;
  return !(left && right && top && bottom);
}

export function drawRleMaskToCanvas({
  canvas,
  maskRle,
  color = DEFAULT_FILL,
  opacity = 0.32,
  contourColor = DEFAULT_CONTOUR,
  contourAlpha = 0.9,
}: DrawMaskOptions): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  const decoded = decodeRle(maskRle);
  if (!decoded) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    return;
  }

  if (canvas.width !== decoded.width || canvas.height !== decoded.height) {
    canvas.width = decoded.width;
    canvas.height = decoded.height;
  }

  const mask = expandMask(decoded);
  const imageData = ctx.createImageData(decoded.width, decoded.height);

  for (let y = 0; y < decoded.height; y += 1) {
    for (let x = 0; x < decoded.width; x += 1) {
      const pixel = y * decoded.width + x;
      const offset = pixel * 4;
      if (!mask[pixel]) {
        imageData.data[offset + 3] = 0;
        continue;
      }

      const edge = isEdgePixel(mask, decoded.width, decoded.height, x, y);
      const [r, g, b] = edge ? contourColor : color;
      imageData.data[offset] = r;
      imageData.data[offset + 1] = g;
      imageData.data[offset + 2] = b;
      imageData.data[offset + 3] = Math.round((edge ? contourAlpha : opacity) * 255);
    }
  }

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.putImageData(imageData, 0, 0);
}

export default function MaskOverlay({ maskRle, className, opacity = 0.32 }: MaskOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (!canvasRef.current) {
      return;
    }
    drawRleMaskToCanvas({ canvas: canvasRef.current, maskRle, opacity });
  }, [maskRle, opacity]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}
    />
  );
}
