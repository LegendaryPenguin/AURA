import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { RefObject } from "react";

type CameraFacingMode = "user" | "environment";

export interface UseCameraReturn {
  videoRef: RefObject<HTMLVideoElement | null>;
  isReady: boolean;
  error: string | null;
  facingMode: CameraFacingMode;
  start: () => Promise<void>;
  stop: () => void;
  toggleFacingMode: () => Promise<void>;
}

export function useCamera(initialFacingMode: CameraFacingMode = "environment"): UseCameraReturn {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [facingMode, setFacingMode] = useState<CameraFacingMode>(initialFacingMode);

  const stop = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsReady(false);
  }, []);

  const start = useCallback(async () => {
    stop();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: facingMode } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setIsReady(true);
      setError(null);
    } catch (unknownError) {
      setIsReady(false);
      setError(unknownError instanceof Error ? unknownError.message : "Unable to start camera");
    }
  }, [facingMode, stop]);

  const toggleFacingMode = useCallback(async () => {
    setFacingMode((value) => (value === "environment" ? "user" : "environment"));
  }, []);

  useEffect(() => {
    void start();
    return () => stop();
  }, [start, stop]);

  useEffect(() => {
    const handleOrientation = () => {
      if (streamRef.current) {
        void start();
      }
    };
    window.addEventListener("orientationchange", handleOrientation);
    return () => window.removeEventListener("orientationchange", handleOrientation);
  }, [start]);

  return useMemo(
    () => ({ videoRef, isReady, error, facingMode, start, stop, toggleFacingMode }),
    [error, facingMode, isReady, start, stop, toggleFacingMode],
  );
}
