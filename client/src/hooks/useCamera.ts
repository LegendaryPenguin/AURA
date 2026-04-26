import { useCallback, useEffect, useMemo, useRef, useState } from "react";

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
  const startingRef = useRef(false);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [facing, setFacing] = useState<CameraFacing>(initialFacing);

  const stopStream = useCallback(() => {
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

  const stop = useCallback(() => {
    startingRef.current = false;
    stopStream();
  }, [stopStream]);

  const start = useCallback(async () => {
    if (startingRef.current) return;
    startingRef.current = true;
    stopStream();
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

      if (!startingRef.current) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }

      streamRef.current = stream;
      const video = videoRef.current;
      if (!video) {
        startingRef.current = false;
        return;
      }

      video.srcObject = stream;
      await new Promise<void>((resolve) => {
        if (video.readyState >= 2) { resolve(); return; }
        video.addEventListener("loadeddata", () => resolve(), { once: true });
      });

      if (!startingRef.current) return;
      await video.play();
      setIsReady(true);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return;
      }
      const msg = err instanceof Error ? err.message : "Camera unavailable";
      setError(msg);
      setIsReady(false);
    } finally {
      startingRef.current = false;
    }
  }, [facing, width, height, stopStream]);

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

  return useMemo(() => ({
    videoRef, isReady, error, start, stop, switchFacing, facing,
  }), [videoRef, isReady, error, start, stop, switchFacing, facing]);
}
