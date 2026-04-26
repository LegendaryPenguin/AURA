import { useState } from "react";

interface CameraControlsProps {
  disabled?: boolean;
  onHoldStart: () => void;
  onHoldEnd: () => void;
  onModeChange?: (mode: "snapshot" | "streaming") => void;
  onAutoScanChange?: (enabled: boolean) => void;
}

export function CameraControls({
  disabled,
  onHoldStart,
  onHoldEnd,
  onModeChange,
  onAutoScanChange,
}: CameraControlsProps) {
  const [mode, setMode] = useState<"snapshot" | "streaming">("snapshot");
  const [autoScan, setAutoScan] = useState(false);
  return (
    <div style={{ display: "flex", gap: 8 }}>
      <button
        type="button"
        disabled={disabled}
        onMouseDown={onHoldStart}
        onMouseUp={onHoldEnd}
        onTouchStart={onHoldStart}
        onTouchEnd={onHoldEnd}
      >
        Hold to Scan
      </button>
      <button
        type="button"
        onClick={() => {
          const next = mode === "snapshot" ? "streaming" : "snapshot";
          setMode(next);
          onModeChange?.(next);
        }}
      >
        Mode: {mode}
      </button>
      <button
        type="button"
        onClick={() => {
          const next = !autoScan;
          setAutoScan(next);
          onAutoScanChange?.(next);
        }}
      >
        Auto Scan: {autoScan ? "On" : "Off"}
      </button>
    </div>
  );
}
