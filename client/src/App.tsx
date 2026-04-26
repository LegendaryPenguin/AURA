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
import type { OverlayResponse, OverlayType, UiLayer } from "./types/overlay";

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
  const [lastResponse, setLastResponse] = useState<OverlayResponse | null>(null);
  const [statusMsg, setStatusMsg] = useState<string>("");
  const [connectionStatus, setConnectionStatus] = useState<"connected" | "disconnected" | "reconnecting">("disconnected");

  const camera = useCamera({
    facing: "environment",
    autoStart: false,
  });

  const audio = useAudioRecorder();
  const { captureFrame } = useFrameCapture();
  const { overlays, replaceOverlays, clearOverlays, hydrateFromResponse } = useOverlay({ autoDismissMs: 60_000 });
  const { fallbackData, isFallbackActive, clearFallback } = useFallback();

  const captureForApi = useCallback(() => {
    const video = camera.videoRef.current;
    if (!video) {
      throw new ApiClientError("Camera video element is not mounted.", "INVALID_RESPONSE");
    }
    if (video.readyState < 2) {
      throw new ApiClientError("Camera is not ready yet. Please wait a moment.", "INVALID_RESPONSE");
    }
    const result = captureFrame(video);
    if (!result) {
      throw new ApiClientError("Could not read a frame from the camera.", "INVALID_RESPONSE");
    }
    const b64 = result.dataUrl.includes(",") ? (result.dataUrl.split(",")[1] ?? result.dataUrl) : result.dataUrl;
    return b64;
  }, [captureFrame, camera.videoRef]);

  const recordAudioForApi = useCallback(async () => {
    if (phaseMode < 2) return undefined;
    return audio.stopRecording();
  }, [phaseMode, audio.stopRecording]);

  const snapshot = useSnapshotAnalysis({
    captureFrame: captureForApi,
    recordAudio: recordAudioForApi,
  });

  const modeName = useMemo(() => phaseLabels[phaseMode] ?? "Unknown", [phaseMode]);

  useEffect(() => {
    if (phaseMode === 0) {
      camera.stop();
      return;
    }
    void camera.start();
    return () => {
      camera.stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phaseMode]);

  useEffect(() => {
    if (phaseMode === 0) {
      clearFallback();
      replaceOverlays([phase0DemoOverlay]);
    } else {
      clearOverlays();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phaseMode]);

  useEffect(() => {
    if (!isFallbackActive || !fallbackData) return;
    const mapped = fallbackData.overlays.map((o, i) => ({
      id: `fallback-${i}`,
      bbox: {
        x: o.bbox[0],
        y: o.bbox[1],
        width: o.bbox[2] - o.bbox[0],
        height: o.bbox[3] - o.bbox[1],
      },
      label: o.label,
      confidence: o.confidence,
      ui_layer: LAYER_BY_INDEX[o.ui_layer] ?? "midground",
      overlay_type: TYPE_BY_NAME[o.overlay_type] ?? "info",
      action_required: o.action_required,
    }));
    replaceOverlays(mapped);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isFallbackActive, fallbackData]);

  useEffect(() => {
    let cancelled = false;
    const checkHealth = async () => {
      try {
        const resp = await fetch("/health");
        if (!resp.ok) throw new Error("not ok");
        const data = await resp.json();
        if (!cancelled) setConnectionStatus(data.status ? "connected" : "disconnected");
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
    if (!camera.isReady) {
      setError("Camera is not ready. Please wait.");
      setStatusMsg("BLOCKED: camera not ready");
      return;
    }
    setError(null);
    setStatusMsg("Sending to server...");
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
      hydrateFromResponse(response);
      setLastResponse(response);
      setStatusMsg(`SUCCESS: ${response.overlays.length} overlay(s) returned`);
    } catch (analyzeError) {
      if (analyzeError instanceof ApiClientError && analyzeError.code === "RATE_LIMITED") {
        setStatusMsg("Rate limited, try again");
        return;
      }
      const msg = analyzeError instanceof ApiClientError
        ? analyzeError.message
        : (analyzeError as Error).message;
      setError(msg);
      setStatusMsg(`ERROR: ${msg}`);
    }
  }, [phaseMode, camera.isReady, camera.videoRef, snapshot.runAnalysis, hydrateFromResponse]);

  const autoScan = useAutoScan({
    intervalMs: 2500,
    onScan: runAnalyze,
    enabled: phaseMode === 3 && camera.isReady,
  });

  const handleCaptureClick = async () => {
    setStatusMsg("Button clicked, calling runAnalyze...");
    await runAnalyze();
  };

  const recordingStarted = useRef(false);

  const handleRecordStart = async () => {
    if (audio.isRecording || recordingStarted.current) return;
    recordingStarted.current = true;
    setError(null);
    setStatusMsg("Recording started...");
    await audio.startRecording();
  };

  const handleRecordStop = async () => {
    if (!recordingStarted.current) return;
    recordingStarted.current = false;
    setStatusMsg("Recording stopped, analyzing...");
    await runAnalyze();
  };

  return (
    <div style={{ minHeight: "100vh", background: "#030712", color: "#f9fafb", padding: "1rem", fontFamily: "Inter, system-ui, sans-serif" }}>
      <header style={styles.header}>
        <h1 style={styles.title}>
          <span style={styles.titleIcon}>&#9673;</span> AURA
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
                {phase} &mdash; {phaseLabels[phase]}
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
          ) : phaseMode >= 2 ? (
            <button
              onPointerDown={() => void handleRecordStart()}
              onPointerUp={() => void handleRecordStop()}
              onPointerLeave={() => void handleRecordStop()}
              disabled={snapshot.isLoading || !camera.isReady}
              style={{
                ...styles.button,
                opacity: snapshot.isLoading ? 0.5 : 1,
                background: audio.isRecording ? "#dc2626" : "#1d4ed8",
                borderColor: audio.isRecording ? "#dc2626" : "#2563eb",
                userSelect: "none",
                touchAction: "none",
              }}
              type="button"
            >
              {snapshot.isLoading
                ? "Analyzing..."
                : audio.isRecording
                  ? "Recording... Release to Analyze"
                  : "Hold to Speak + Capture"}
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
              {snapshot.isLoading ? "Analyzing..." : "Capture + Analyze"}
            </button>
          )}

          {phaseMode >= 2 && (
            <button
              onClick={() => void camera.switchFacing()}
              style={styles.buttonSecondary}
              type="button"
              title="Switch camera"
            >
              &#10226;
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
        <OverlayCanvas overlays={overlays} />
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

      {/* Status message - always visible */}
      <div style={{
        padding: "0.5rem 0.75rem",
        background: statusMsg.startsWith("ERROR") ? "#7f1d1d" : statusMsg.startsWith("SUCCESS") ? "#064e3b" : "#1e293b",
        borderRadius: "0.4rem",
        fontSize: "0.85rem",
        minHeight: "1.5rem",
        fontFamily: "monospace",
        color: statusMsg.startsWith("ERROR") ? "#fca5a5" : statusMsg.startsWith("SUCCESS") ? "#6ee7b7" : "#94a3b8",
      }}>
        {statusMsg || `Ready | Phase ${phaseMode} | Camera: ${camera.isReady ? "ready" : "not ready"} | Server: ${connectionStatus}`}
      </div>

      {(error || camera.error || autoScan.lastError) && (
        <div style={styles.errorBar}>
          {error && <span>Error: {error}</span>}
          {camera.error && <span>Camera: {camera.error}</span>}
          {autoScan.lastError && <span>Scan: {autoScan.lastError}</span>}
        </div>
      )}

      {lastResponse && lastResponse.overlays.length > 0 && (
        <div style={styles.resultsPanel}>
          <strong>Analysis Results ({lastResponse.overlays.length} overlay{lastResponse.overlays.length !== 1 ? "s" : ""}):</strong>
          {lastResponse.overlays.map((o, i) => (
            <div key={i} style={styles.resultItem}>
              <span style={styles.resultLabel}>{o.label}</span>
              <span style={styles.resultConf}>{(o.confidence * 100).toFixed(0)}%</span>
              <span style={styles.resultType}>{o.overlay_type}</span>
              <span style={styles.resultBbox}>
                ({o.bbox.x.toFixed(2)}, {o.bbox.y.toFixed(2)}) {o.bbox.width.toFixed(2)}x{o.bbox.height.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      )}

      <StatusBar
        serverStatus={connectionStatus}
        modelWarm={connectionStatus === "connected"}
        currentPhase={phaseMode}
      />

      <footer style={styles.statusInfo}>
        <span>Mode: {modeName}</span>
        <span>Camera: {camera.isReady || phaseMode === 0 ? "ready" : "not ready"} ({camera.facing})</span>
        <span>Overlays: {overlays.length}</span>
        {phaseMode === 3 && (
          <span>Scans: {autoScan.scanCount} | {autoScan.isAutoScanning ? "running" : "stopped"}</span>
        )}
        {snapshot.error && <span style={styles.errorText}>API: {snapshot.error}</span>}
      </footer>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: "0.75rem",
    marginBottom: "0.5rem",
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
    margin: "0.5rem auto",
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
    fontSize: "0.85rem",
    color: "#fca5a5",
    padding: "0.6rem 0.8rem",
    background: "rgba(127, 29, 29, 0.4)",
    borderRadius: "0.5rem",
    marginTop: "0.25rem",
  },
  statusInfo: {
    display: "flex",
    flexWrap: "wrap",
    gap: "1rem",
    alignItems: "center",
    fontSize: "0.8rem",
    borderTop: "1px solid #1f2937",
    paddingTop: "0.5rem",
    marginTop: "0.5rem",
    opacity: 0.7,
  },
  errorText: {
    color: "#fca5a5",
  },
  resultsPanel: {
    padding: "0.75rem 1rem",
    background: "rgba(16, 185, 129, 0.15)",
    border: "2px solid #10b981",
    borderRadius: "0.5rem",
    fontSize: "0.9rem",
    display: "flex",
    flexDirection: "column",
    gap: "0.4rem",
    marginTop: "0.25rem",
  },
  resultItem: {
    display: "flex",
    gap: "0.75rem",
    alignItems: "center",
    paddingLeft: "0.5rem",
  },
  resultLabel: {
    color: "#6ee7b7",
    fontWeight: 600,
    fontSize: "1rem",
  },
  resultConf: {
    color: "#a7f3d0",
    fontSize: "0.85rem",
  },
  resultType: {
    color: "#86efac",
    fontSize: "0.75rem",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    opacity: 0.7,
  },
  resultBbox: {
    color: "#6b7280",
    fontSize: "0.75rem",
    fontFamily: "monospace",
  },
};
