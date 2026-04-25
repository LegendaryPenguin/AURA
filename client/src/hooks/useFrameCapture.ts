import { useCallback, useRef } from "react";

export interface CaptureResult {
  dataUrl: string;
  width: number;
  height: number;
}

export interface FrameCaptureHook {
  captureFrame: (videoElement: HTMLVideoElement | null) => CaptureResult | null;
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

    return {
      dataUrl,
      width,
      height
    };
  }, []);

  return { captureFrame };
}
