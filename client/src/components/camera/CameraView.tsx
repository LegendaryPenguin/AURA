import type { RefObject } from "react";

interface CameraViewProps {
  videoRef: RefObject<HTMLVideoElement | null>;
}

export function CameraView({ videoRef }: CameraViewProps) {
  return (
    <video
      ref={videoRef}
      muted
      autoPlay
      playsInline
      style={{ width: "100vw", height: "100vh", objectFit: "cover", background: "#000" }}
    />
  );
}
