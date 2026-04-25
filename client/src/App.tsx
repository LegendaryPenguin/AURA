import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import OverlayCanvas from "./components/overlays/OverlayCanvas";
import { useFallback } from "./hooks/useFallback";
import { useFrameCapture } from "./hooks/useFrameCapture";
import { useOverlay } from "./hooks/useOverlay";
import { useSnapshotAnalysis } from "./hooks/useSnapshotAnalysis";
import { ApiClientError } from "./services/api";
import type { OverlayType, UiLayer } from "../../shared/schemas/types";

const PHASES = [0, 1, 2, 3, 4, 5] as const;
const phaseLabels: Record<number, string> = {
  0: "Fallback",
  1: "Snapshot",
  2: "Live Camera + Voice",
  3: "Auto-Scan",
  4: "Tracked AR",
  5: "Real-Time Streaming",
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
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [phaseMode, setPhaseMode] = useState(1);
  const [isCameraReady, setIsCameraReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { captureFrame } = useFrameCapture();
  const overlay = useOverlay({ autoDismissMs: 60_000 });
  const { fallbackData, isFallbackActive, clearFallback } = useFallback();

  const captureForApi = useCallback(() => {
    const result = captureFrame(videoRef.current);
    if (!result) {
      throw new ApiClientError("Could not read a frame from the camera.", "INVALID_RESPONSE");
    }
    const b64 = result.dataUrl.includes(",") ? (result.dataUrl.split(",")[1] ?? result.dataUrl) : result.dataUrl;
    return b64;
  }, [captureFrame]);

  const snapshot = useSnapshotAnalysis({ captureFrame: captureForApi });

  const modeName = useMemo(() => phaseLabels[phaseMode] ?? "Unknown", [phaseMode]);

  useEffect(() => {
    let stream: MediaStream | null = null;

    const startCamera = async () => {
      if (phaseMode === 0) {
        setIsCameraReady(false);
        return;
      }

      try {
        setError(null);
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
          audio: false,
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
          setIsCameraReady(true);
        }
      } catch (cameraError) {
        setError(`Camera unavailable: ${(cameraError as Error).message}`);
        setIsCameraReady(false);
      }
    };

    void startCamera();

    return () => {
      if (videoRef.current) {
        videoRef.current.pause();
        videoRef.current.srcObject = null;
      }
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
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
    if (!isFallbackActive || !fallbackData) {
      return;
    }
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

  const runAnalyze = async () => {
    if (phaseMode === 0) {
      return;
    }
    setError(null);
    try {
      const w = videoRef.current?.videoWidth ?? 0;
      const h = videoRef.current?.videoHeight ?? 0;
      const response = await snapshot.runAnalysis({
        query: "What am I looking at?",
        sessionId: "aura-app-shell",
        captureTsMs: Date.now(),
        frameSize: w > 0 && h > 0 ? { width: w, height: h } : undefined,
        client: { platform: "web" },
      });
      overlay.hydrateFromResponse(response);
    } catch (analyzeError) {
      setError(
        analyzeError instanceof ApiClientError
          ? analyzeError.message
          : (analyzeError as Error).message,
      );
    }
  };

  return (
    <main style={styles.app}>
      <header style={styles.header}>
        <h1 style={styles.title}>AURA App Shell</h1>
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
          <button
            onClick={() => {
              void runAnalyze();
            }}
            disabled={snapshot.isLoading || phaseMode === 0}
            style={styles.button}
            type="button"
          >
            {snapshot.isLoading ? "Analyzing..." : "Capture + Analyze"}
          </button>
        </div>
      </header>

      <section style={styles.stage}>
        {phaseMode === 0 ? (
          <video
            ref={videoRef}
            style={styles.video}
            controls
            loop
            autoPlay
            muted
            src="https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"
          />
        ) : (
          <video ref={videoRef} style={styles.video} muted playsInline />
        )}
        <OverlayCanvas overlays={overlay.overlays} />
      </section>

      <footer style={styles.statusBar}>
        <span>Mode: {modeName}</span>
        <span>Camera: {isCameraReady || phaseMode === 0 ? "ready" : "not ready"}</span>
        <span>Overlay count: {overlay.overlays.length}</span>
        {error ? <span style={styles.error}>Error: {error}</span> : <span>Connection: ready</span>}
        {snapshot.error ? <span style={styles.error}>API: {snapshot.error}</span> : null}
      </footer>
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    minHeight: "100vh",
    display: "grid",
    gridTemplateRows: "auto 1fr auto",
    gap: "0.75rem",
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
  statusBar: {
    display: "flex",
    flexWrap: "wrap",
    gap: "1rem",
    alignItems: "center",
    fontSize: "0.875rem",
    borderTop: "1px solid #1f2937",
    paddingTop: "0.75rem",
  },
  error: {
    color: "#fca5a5",
  },
};
