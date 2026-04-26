import { useCallback, useRef } from "react";

export interface CaptureResult {
  dataUrl: string;
  width: number;
  height: number;
  sharpnessScore: number;
}

export interface FrameCaptureHook {
  captureFrame: (videoElement: HTMLVideoElement | null) => CaptureResult | null;
  captureBurst: (
    videoElement: HTMLVideoElement | null,
    count: number,
    intervalMs?: number,
  ) => Promise<CaptureResult[]>;
}

function resolveCaptureSize(videoElement: HTMLVideoElement): { width: number; height: number } {
  const width = videoElement.videoWidth || videoElement.clientWidth;
  const height = videoElement.videoHeight || videoElement.clientHeight;

  return {
    width: Math.max(0, Math.floor(width)),
    height: Math.max(0, Math.floor(height))
  };
}

export function useFrameCapture(): FrameCaptureHook {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const calculateSharpness = useCallback((canvas: HTMLCanvasElement): number => {
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (!context) {
      return 0;
    }
    const { width, height } = canvas;
    const imageData = context.getImageData(0, 0, width, height).data;
    if (width < 3 || height < 3) {
      return 0;
    }
    let laplacianEnergy = 0;
    for (let y = 1; y < height - 1; y += 1) {
      for (let x = 1; x < width - 1; x += 1) {
        const idx = (y * width + x) * 4;
        const luma = 0.299 * imageData[idx] + 0.587 * imageData[idx + 1] + 0.114 * imageData[idx + 2];
        const left = ((y * width + (x - 1)) * 4);
        const right = ((y * width + (x + 1)) * 4);
        const up = (((y - 1) * width + x) * 4);
        const down = (((y + 1) * width + x) * 4);
        const lumaLeft = 0.299 * imageData[left] + 0.587 * imageData[left + 1] + 0.114 * imageData[left + 2];
        const lumaRight = 0.299 * imageData[right] + 0.587 * imageData[right + 1] + 0.114 * imageData[right + 2];
        const lumaUp = 0.299 * imageData[up] + 0.587 * imageData[up + 1] + 0.114 * imageData[up + 2];
        const lumaDown = 0.299 * imageData[down] + 0.587 * imageData[down + 1] + 0.114 * imageData[down + 2];
        const lap = (4 * luma) - lumaLeft - lumaRight - lumaUp - lumaDown;
        laplacianEnergy += lap * lap;
      }
    }
    return laplacianEnergy / ((width - 2) * (height - 2));
  }, []);

  const captureFrame = useCallback((videoElement: HTMLVideoElement | null): CaptureResult | null => {
    if (!videoElement) {
      return null;
    }

    const { width, height } = resolveCaptureSize(videoElement);
    if (width <= 0 || height <= 0) {
      return null;
    }

    const canvas = canvasRef.current ?? document.createElement("canvas");
    if (!canvasRef.current) {
      canvasRef.current = canvas;
    }

    canvas.width = width;
    canvas.height = height;

    const context = canvas.getContext("2d");
    if (!context) {
      return null;
    }

    context.drawImage(videoElement, 0, 0, width, height);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.85);

    const sharpnessScore = calculateSharpness(canvas);
    return {
      dataUrl,
      width,
      height,
      sharpnessScore,
    };
  }, [calculateSharpness]);

  const captureBurst = useCallback(
    async (videoElement: HTMLVideoElement | null, count: number, intervalMs = 90): Promise<CaptureResult[]> => {
      const shots: CaptureResult[] = [];
      const total = Math.max(1, Math.floor(count));
      for (let i = 0; i < total; i += 1) {
        const shot = captureFrame(videoElement);
        if (shot) {
          shots.push(shot);
        }
        if (i < total - 1) {
          await new Promise<void>((resolve) => window.setTimeout(resolve, intervalMs));
        }
      }
      return shots;
    },
    [captureFrame],
  );

  return { captureFrame, captureBurst };
}
