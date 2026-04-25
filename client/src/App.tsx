import { useEffect, useMemo, useRef, useState } from "react";

type OverlayBox = {
  id: string;
  label: string;
  confidence: number;
  x: number;
  y: number;
  width: number;
  height: number;
};

type AnalyzeResponse = {
  overlays: OverlayBox[];
};

const PHASES = [0, 1, 2, 3, 4, 5] as const;
const phaseLabels: Record<number, string> = {
  0: "Fallback",
  1: "Snapshot",
  2: "Live Camera + Voice",
  3: "Auto-Scan",
  4: "Tracked AR",
  5: "Real-Time Streaming",
};

const fallbackPayload: AnalyzeResponse = {
  overlays: [
    {
      id: "fallback-1",
      label: "Demo object",
      confidence: 0.93,
      x: 0.22,
      y: 0.24,
      width: 0.32,
      height: 0.28,
    },
  ],
};

function drawOverlays(canvas: HTMLCanvasElement, overlays: OverlayBox[]): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.lineWidth = 3;
  ctx.font = "14px Inter, system-ui, sans-serif";
  ctx.textBaseline = "top";

  overlays.forEach((overlay) => {
    const x = overlay.x * canvas.width;
    const y = overlay.y * canvas.height;
    const width = overlay.width * canvas.width;
    const height = overlay.height * canvas.height;

    ctx.strokeStyle = "#22c55e";
    ctx.fillStyle = "rgba(34, 197, 94, 0.15)";
    ctx.strokeRect(x, y, width, height);
    ctx.fillRect(x, y, width, height);

    const label = `${overlay.label} ${(overlay.confidence * 100).toFixed(0)}%`;
    ctx.fillStyle = "#111827";
    ctx.fillRect(x, Math.max(0, y - 22), ctx.measureText(label).width + 12, 20);
    ctx.fillStyle = "#f9fafb";
    ctx.fillText(label, x + 6, Math.max(0, y - 20) + 3);
  });
}

export default function App() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [phaseMode, setPhaseMode] = useState<number>(2);
  const [isLoading, setIsLoading] = useState(false);
  const [isCameraReady, setIsCameraReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<AnalyzeResponse>(fallbackPayload);

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
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    drawOverlays(canvas, lastResponse.overlays);
  }, [lastResponse]);

  const runAnalyze = async () => {
    setIsLoading(true);
    setError(null);

    try {
      if (phaseMode === 0) {
        setLastResponse(fallbackPayload);
        return;
      }

      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phaseMode,
          prompt: "What am I looking at?",
          timestamp: Date.now(),
        }),
      });

      if (!response.ok) {
        throw new Error(`Analyze failed with status ${response.status}`);
      }

      const payload = (await response.json()) as AnalyzeResponse;
      setLastResponse(payload.overlays?.length ? payload : fallbackPayload);
    } catch (analyzeError) {
      setError((analyzeError as Error).message);
      setLastResponse(fallbackPayload);
    } finally {
      setIsLoading(false);
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
          <button onClick={runAnalyze} disabled={isLoading} style={styles.button} type="button">
            {isLoading ? "Analyzing..." : "Capture + Analyze"}
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
        <canvas ref={canvasRef} width={960} height={540} style={styles.canvas} />
      </section>

      <footer style={styles.statusBar}>
        <span>Mode: {modeName}</span>
        <span>Camera: {isCameraReady || phaseMode === 0 ? "ready" : "not ready"}</span>
        <span>Overlay count: {lastResponse.overlays.length}</span>
        {error ? <span style={styles.error}>Error: {error}</span> : <span>Connection: healthy</span>}
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
  canvas: {
    position: "absolute",
    inset: 0,
    width: "100%",
    height: "100%",
    pointerEvents: "none",
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
