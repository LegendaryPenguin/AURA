import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import OverlayCanvas from "./components/overlays/OverlayCanvas";
import { StatusBar } from "./components/ui/StatusBar";
import { ScanAnimation } from "./components/ui/ScanAnimation";
import { useFallback } from "./hooks/useFallback";
import { useFrameCapture } from "./hooks/useFrameCapture";
import { useOverlay } from "./hooks/useOverlay";
import { useSnapshotAnalysis } from "./hooks/useSnapshotAnalysis";
import { useCamera } from "./hooks/useCamera";
import { useAudioRecorder } from "./hooks/useAudioRecorder";
import { useAutoScan } from "./hooks/useAutoScan";
import { ApiClientError } from "./services/api";
import type { OverlayType, UiLayer } from "../../shared/schemas/types";

const PHASES = [0, 1, 2, 3] as const;
const phaseLabels: Record<number, string> = {
  0: "Fallback",
  1: "Snapshot",
  2: "Live Camera + Voice",
  3: "Auto-Scan",
};

const LAYER_BY_INDEX: readonly UiLayer[] = ["background", "midground", "foreground", "hud"] as const;
const TYPE_BY_NAME: Record<string, OverlayType> = {
  diagnostic: "diagnostic",
  hazard: "hazard",
  info: "info",
  reference: "reference",
};

const phase0DemoOverlay = {
  bbox: { x: 0.22, y: 0.24, width: 0.32, height: 0.28 },
  label: "Demo object",
  confidence: 0.93,
  ui_layer: "midground" as const,
  overlay_type: "info" as const,
  action_required: false,
};

export default function App() {
  const [phaseMode, setPhaseMode] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<"connected" | "disconnected" | "reconnecting">("disconnected");

  const camera = useCamera({
    facing: "environment",
    autoStart: false,
  });

  const audio = useAudioRecorder();
  const { captureFrame } = useFrameCapture();
  const overlay = useOverlay({ autoDismissMs: 60_000 });
  const { fallbackData, isFallbackActive, clearFallback } = useFallback();

  const captureForApi = useCallback(() => {
    const result = captureFrame(camera.videoRef.current);
    if (!result) {
      throw new ApiClientError("Could not read a frame from the camera.", "INVALID_RESPONSE");
    }
    const b64 = result.dataUrl.includes(",") ? (result.dataUrl.split(",")[1] ?? result.dataUrl) : result.dataUrl;
    return b64;
  }, [captureFrame, camera.videoRef]);

  const recordAudioForApi = useCallback(async () => {
    if (phaseMode < 2) return undefined;
    return audio.stopRecording();
  }, [phaseMode, audio]);

  const snapshot = useSnapshotAnalysis({
    captureFrame: captureForApi,
    recordAudio: recordAudioForApi,
  });

  const modeName = useMemo(() => phaseLabels[phaseMode] ?? "Unknown", [phaseMode]);

  useEffect(() => {
    if (phaseMode === 0) {
      camera.stop();
    } else {
      void camera.start();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phaseMode]);

  useEffect(() => {
    if (phaseMode === 0) {
      clearFallback();
      overlay.replaceOverlays([phase0DemoOverlay]);
    } else {
      overlay.clearOverlays();
    }
  }, [phaseMode, clearFallback, overlay]);

  useEffect(() => {
    if (!isFallbackActive || !fallbackData) return;
    const mapped = fallbackData.overlays.map((o, i) => ({
      id: `fallback-${i}`,
      bbox: { x: o.bbox[0], y: o.bbox[1], width: o.bbox[2], height: o.bbox[3] },
      label: o.label,
      confidence: o.confidence,
      ui_layer: LAYER_BY_INDEX[o.ui_layer] ?? "midground",
      overlay_type: TYPE_BY_NAME[o.overlay_type] ?? "info",
      action_required: o.action_required,
    }));
    overlay.replaceOverlays(mapped);
  }, [isFallbackActive, fallbackData, overlay]);

  // Health check to set connection status
  useEffect(() => {
    let cancelled = false;
    const checkHealth = async () => {
      try {
        const { getHealth } = await import("./services/api");
        const h = await getHealth();
        if (!cancelled) setConnectionStatus(h.status ? "connected" : "disconnected");
      } catch {
        if (!cancelled) setConnectionStatus("disconnected");
      }
    };
    void checkHealth();
    const interval = setInterval(() => void checkHealth(), 10000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const runAnalyze = useCallback(async () => {
    if (phaseMode === 0) return;
    setError(null);
    try {
      const w = camera.videoRef.current?.videoWidth ?? 0;
      const h = camera.videoRef.current?.videoHeight ?? 0;
      const response = await snapshot.runAnalysis({
        query: "What am I looking at?",
        sessionId: "aura-app-shell",
        captureTsMs: Date.now(),
        frameSize: w > 0 && h > 0 ? { width: w, height: h } : undefined,
        client: { platform: "web" },
      });
      overlay.hydrateFromResponse(response);
    } catch (analyzeError) {
      if (analyzeError instanceof ApiClientError && analyzeError.code === "RATE_LIMITED") {
        return;
      }
      setError(
        analyzeError instanceof ApiClientError
          ? analyzeError.message
          : (analyzeError as Error).message,
      );
    }
  }, [phaseMode, camera.videoRef, snapshot, overlay]);

  const autoScan = useAutoScan({
    intervalMs: 2500,
    onScan: runAnalyze,
    enabled: phaseMode === 3 && camera.isReady,
  });

  const handleCaptureClick = async () => {
    if (phaseMode >= 2 && !audio.isRecording) {
      await audio.startRecording();
      setTimeout(async () => {
        await runAnalyze();
      }, 500);
    } else {
      await runAnalyze();
    }
  };

  return (
    <main style={styles.app}>
      <header style={styles.header}>
        <h1 style={styles.title}>
          <span style={styles.titleIcon}>◉</span> AURA
        </h1>
        <div style={styles.headerRight}>
          <label htmlFor="phase-select" style={styles.label}>
            Phase
          </label>
          <select
            id="phase-select"
            value={phaseMode}
            onChange={(event) => setPhaseMode(Number(event.target.value))}
            style={styles.select}
          >
            {PHASES.map((phase) => (
              <option key={phase} value={phase}>
                {phase} — {phaseLabels[phase]}
              </option>
            ))}
          </select>

          {phaseMode === 3 ? (
            <button
              onClick={autoScan.toggleAutoScan}
              style={{
                ...styles.button,
                background: autoScan.isAutoScanning ? "#dc2626" : "#059669",
                borderColor: autoScan.isAutoScanning ? "#dc2626" : "#059669",
              }}
              type="button"
            >
              {autoScan.isAutoScanning ? `Stop Scan (${autoScan.scanCount})` : "Start Auto-Scan"}
            </button>
          ) : (
            <button
              onClick={() => void handleCaptureClick()}
              disabled={snapshot.isLoading || phaseMode === 0 || (!camera.isReady && phaseMode > 0)}
              style={{
                ...styles.button,
                opacity: snapshot.isLoading || phaseMode === 0 ? 0.5 : 1,
              }}
              type="button"
            >
              {snapshot.isLoading
                ? "Analyzing..."
                : phaseMode >= 2
                  ? "Hold to Speak + Capture"
                  : "Capture + Analyze"}
            </button>
          )}

          {phaseMode >= 2 && (
            <button
              onClick={() => void camera.switchFacing()}
              style={styles.buttonSecondary}
              type="button"
              title="Switch camera"
            >
              ⟲
            </button>
          )}
        </div>
      </header>

      <section style={styles.stage}>
        {phaseMode === 0 ? (
          <video
            style={styles.video}
            controls
            loop
            autoPlay
            muted
            src="https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"
          />
        ) : (
          <video ref={camera.videoRef} style={styles.video} muted playsInline />
        )}
        <OverlayCanvas overlays={overlay.overlays} />
        {(snapshot.isLoading || autoScan.isAutoScanning) && (
          <ScanAnimation isScanning={true} />
        )}
        {audio.isRecording && (
          <div style={styles.recordingIndicator}>
            <span style={styles.recordingDot} />
            Recording...
          </div>
        )}
      </section>

      <StatusBar
        serverStatus={connectionStatus}
        modelWarm={connectionStatus === "connected"}
        currentPhase={phaseMode}
      />

      {(error || camera.error || autoScan.lastError) && (
        <div style={styles.errorBar}>
          {error && <span>Error: {error}</span>}
          {camera.error && <span>Camera: {camera.error}</span>}
          {autoScan.lastError && <span>Scan: {autoScan.lastError}</span>}
        </div>
      )}

      <footer style={styles.statusInfo}>
        <span>Mode: {modeName}</span>
        <span>Camera: {camera.isReady || phaseMode === 0 ? "ready" : "not ready"} ({camera.facing})</span>
        <span>Overlays: {overlay.overlays.length}</span>
        {phaseMode === 3 && (
          <span>Scans: {autoScan.scanCount} | {autoScan.isAutoScanning ? "running" : "stopped"}</span>
        )}
        {snapshot.error && <span style={styles.errorText}>API: {snapshot.error}</span>}
      </footer>
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    minHeight: "100vh",
    display: "grid",
    gridTemplateRows: "auto 1fr auto auto auto",
    gap: "0.5rem",
    background: "#030712",
    color: "#f9fafb",
    padding: "1rem",
    fontFamily: "Inter, system-ui, sans-serif",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: "0.75rem",
  },
  title: {
    fontSize: "1.25rem",
    margin: 0,
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
  },
  titleIcon: {
    color: "#3b82f6",
    fontSize: "1.4rem",
  },
  headerRight: {
    display: "flex",
    gap: "0.5rem",
    alignItems: "center",
    flexWrap: "wrap",
  },
  label: {
    fontSize: "0.875rem",
    opacity: 0.9,
  },
  select: {
    padding: "0.45rem 0.6rem",
    borderRadius: "0.45rem",
    border: "1px solid #374151",
    background: "#111827",
    color: "#f9fafb",
  },
  button: {
    padding: "0.45rem 0.7rem",
    borderRadius: "0.45rem",
    border: "1px solid #2563eb",
    background: "#1d4ed8",
    color: "#fff",
    cursor: "pointer",
    fontWeight: 500,
    transition: "opacity 0.2s",
  },
  buttonSecondary: {
    padding: "0.45rem 0.6rem",
    borderRadius: "0.45rem",
    border: "1px solid #374151",
    background: "#1f2937",
    color: "#f9fafb",
    cursor: "pointer",
    fontSize: "1.1rem",
  },
  stage: {
    position: "relative",
    width: "100%",
    maxWidth: "960px",
    margin: "0 auto",
    aspectRatio: "16 / 9",
    borderRadius: "0.75rem",
    overflow: "hidden",
    border: "1px solid #1f2937",
    background: "#000",
  },
  video: {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    display: "block",
  },
  recordingIndicator: {
    position: "absolute",
    top: "0.75rem",
    right: "0.75rem",
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
    padding: "0.3rem 0.6rem",
    borderRadius: "9999px",
    background: "rgba(220, 38, 38, 0.85)",
    color: "#fff",
    fontSize: "0.75rem",
    fontWeight: 600,
  },
  recordingDot: {
    display: "inline-block",
    width: "0.5rem",
    height: "0.5rem",
    borderRadius: "50%",
    background: "#fff",
    animation: "pulse 1s ease-in-out infinite",
  },
  errorBar: {
    display: "flex",
    flexWrap: "wrap",
    gap: "1rem",
    fontSize: "0.8rem",
    color: "#fca5a5",
    padding: "0.5rem",
    background: "rgba(127, 29, 29, 0.3)",
    borderRadius: "0.5rem",
  },
  statusInfo: {
    display: "flex",
    flexWrap: "wrap",
    gap: "1rem",
    alignItems: "center",
    fontSize: "0.8rem",
    borderTop: "1px solid #1f2937",
    paddingTop: "0.5rem",
    opacity: 0.7,
  },
  errorText: {
    color: "#fca5a5",
  },
};
