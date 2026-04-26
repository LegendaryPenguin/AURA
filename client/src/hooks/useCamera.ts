import { useCallback, useEffect, useRef, useState } from "react";

export type CameraFacing = "user" | "environment";

export interface UseCameraOptions {
  facing?: CameraFacing;
  width?: number;
  height?: number;
  autoStart?: boolean;
}

export interface UseCameraReturn {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  isReady: boolean;
  error: string | null;
  start: () => Promise<void>;
  stop: () => void;
  switchFacing: () => Promise<void>;
  facing: CameraFacing;
}

export function useCamera(options: UseCameraOptions = {}): UseCameraReturn {
  const {
    facing: initialFacing = "environment",
    width = 1280,
    height = 720,
    autoStart = false,
  } = options;

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [facing, setFacing] = useState<CameraFacing>(initialFacing);

  const stop = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.srcObject = null;
    }
    setIsReady(false);
  }, []);

  const start = useCallback(async () => {
    stop();
    setError(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: facing,
          width: { ideal: width },
          height: { ideal: height },
        },
        audio: false,
      });
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setIsReady(true);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Camera unavailable";
      setError(msg);
      setIsReady(false);
    }
  }, [facing, width, height, stop]);

  const switchFacing = useCallback(async () => {
    const next = facing === "environment" ? "user" : "environment";
    setFacing(next);
  }, [facing]);

  useEffect(() => {
    if (facing && isReady) {
      void start();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facing]);

  useEffect(() => {
    if (autoStart) {
      void start();
    }
    return stop;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { videoRef, isReady, error, start, stop, switchFacing, facing };
}
