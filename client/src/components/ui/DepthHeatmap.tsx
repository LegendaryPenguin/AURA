import { useRef, useEffect, CSSProperties } from 'react';

export interface DepthHeatmapProps {
  depthMap: Float32Array | null;
  width: number;
  height: number;
}

function depthToColor(normalizedDepth: number): [number, number, number] {
  const t = Math.max(0, Math.min(1, normalizedDepth));

  if (t < 0.25) {
    const s = t / 0.25;
    return [255, Math.round(s * 165), 0];
  } else if (t < 0.5) {
    const s = (t - 0.25) / 0.25;
    return [Math.round(255 * (1 - s)), 255, 0];
  } else if (t < 0.75) {
    const s = (t - 0.5) / 0.25;
    return [0, Math.round(255 * (1 - s)), Math.round(255 * s)];
  } else {
    const s = (t - 0.75) / 0.25;
    return [Math.round(75 * s), 0, Math.round(255 * (1 - s * 0.3))];
  }
}

export function DepthHeatmap({ depthMap, width, height }: DepthHeatmapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !depthMap || depthMap.length === 0) return;

    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const imageData = ctx.createImageData(width, height);
    const pixels = imageData.data;

    let minDepth = Infinity;
    let maxDepth = -Infinity;
    for (let i = 0; i < depthMap.length; i++) {
      if (depthMap[i] < minDepth) minDepth = depthMap[i];
      if (depthMap[i] > maxDepth) maxDepth = depthMap[i];
    }

    const range = maxDepth - minDepth || 1;

    for (let i = 0; i < depthMap.length; i++) {
      const normalized = (depthMap[i] - minDepth) / range;
      const [r, g, b] = depthToColor(normalized);
      const pixelIdx = i * 4;
      pixels[pixelIdx] = r;
      pixels[pixelIdx + 1] = g;
      pixels[pixelIdx + 2] = b;
      pixels[pixelIdx + 3] = 200;
    }

    ctx.putImageData(imageData, 0, 0);
  }, [depthMap, width, height]);

  if (!depthMap) return null;

  const containerStyle: CSSProperties = {
    position: 'absolute',
    inset: 0,
    pointerEvents: 'none',
    zIndex: 30,
    opacity: 0.6,
  };

  return (
    <div style={containerStyle} data-testid="depth-heatmap">
      <canvas
        ref={canvasRef}
        style={{ width: '100%', height: '100%' }}
      />
    </div>
  );
}
