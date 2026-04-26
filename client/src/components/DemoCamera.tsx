import { useEffect, useMemo, useRef, useState } from "react";
import { DemoOverlayRenderer } from "./DemoOverlayRenderer";
import { FREE_SCAN_COPY, MATH_BASELINE_COPY, type DemoScenario, type DemoScenarioId } from "../data/demoScenarios";
import { detectScenarioFromCapture } from "../utils/sceneMatcher";

interface DemoCameraProps {
  scenarioId: DemoScenarioId;
  scenario?: DemoScenario;
  showLockedResult: boolean;
  lockedCaptureDataUrl: string | null;
  onExitLockedResult: () => void;
  onSelectScenario: (scenarioId: DemoScenarioId) => void;
  onCaptureComplete: (capturedDataUrl: string, target?: "result" | "locked", detectedScenarioId?: DemoScenarioId) => void;
}

const scenarioButtons: Array<{ id: DemoScenarioId; label: string }> = [
  { id: "math", label: "Math Baseline" },
  { id: "care", label: "Care Safety Scan" },
  { id: "sustainability", label: "Sustainability Audit" },
  { id: "wayfinding", label: "Wayfinding Assistant" },
  { id: "free", label: "Free Scan" },
];

export function DemoCamera({
  scenarioId,
  scenario,
  showLockedResult,
  lockedCaptureDataUrl,
  onExitLockedResult,
  onSelectScenario,
  onCaptureComplete,
}: DemoCameraProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const guideRef = useRef<HTMLDivElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzeStep, setAnalyzeStep] = useState(0);

  const analyzeSteps = useMemo(
    () => ["Locking spatial anchors", "Projecting overlays"] as const,
    [],
  );

  useEffect(() => {
    const startCamera = async () => {
      try {
        setError(null);
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: "environment" },
          },
          audio: false,
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        setCameraReady(true);
      } catch (err) {
        setError((err as Error).message || "Unable to open camera");
        setCameraReady(false);
      }
    };

    void startCamera();

    return () => {
      if (videoRef.current) {
        videoRef.current.pause();
        videoRef.current.srcObject = null;
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  useEffect(() => {
    if (!isAnalyzing) {
      return;
    }
    let step = 0;
    setAnalyzeStep(0);
    const interval = window.setInterval(() => {
      step += 1;
      setAnalyzeStep(Math.min(step, analyzeSteps.length - 1));
    }, 480);
    return () => window.clearInterval(interval);
  }, [analyzeSteps.length, isAnalyzing]);

  const captureFromGuide = (): string | null => {
    const video = videoRef.current;
    const guide = guideRef.current;
    if (!video || !guide) {
      return null;
    }
    const sourceWidth = video.videoWidth;
    const sourceHeight = video.videoHeight;
    if (!sourceWidth || !sourceHeight) {
      return null;
    }

    const videoRect = video.getBoundingClientRect();
    const guideRect = guide.getBoundingClientRect();
    const viewportWidth = videoRect.width;
    const viewportHeight = videoRect.height;
    if (!viewportWidth || !viewportHeight) {
      return null;
    }

    // Mirror CSS object-fit: cover mapping from source frame to viewport.
    const scale = Math.max(viewportWidth / sourceWidth, viewportHeight / sourceHeight);
    const renderedWidth = sourceWidth * scale;
    const renderedHeight = sourceHeight * scale;
    const offsetX = (viewportWidth - renderedWidth) / 2;
    const offsetY = (viewportHeight - renderedHeight) / 2;

    const guideX = guideRect.left - videoRect.left;
    const guideY = guideRect.top - videoRect.top;

    const srcX = Math.max(0, (guideX - offsetX) / scale);
    const srcY = Math.max(0, (guideY - offsetY) / scale);
    const srcWidth = Math.min(sourceWidth - srcX, guideRect.width / scale);
    const srcHeight = Math.min(sourceHeight - srcY, guideRect.height / scale);
    if (srcWidth <= 0 || srcHeight <= 0) {
      return null;
    }

    const canvas = document.createElement("canvas");
    canvas.width = 1200;
    canvas.height = 900;
    const context = canvas.getContext("2d");
    if (!context) {
      return null;
    }
    context.drawImage(video, srcX, srcY, srcWidth, srcHeight, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.92);
  };

  const handleCapture = async () => {
    if (!videoRef.current) {
      setError("Camera not ready");
      return;
    }
    const captureDataUrl = captureFromGuide();
    if (!captureDataUrl) {
      setError("Capture failed. Try again.");
      return;
    }

    try {
      if (scenarioId === "free" || scenarioId === "math") {
        onCaptureComplete(captureDataUrl, "result", scenarioId);
        return;
      }

      const detectedScenarioId = await detectScenarioFromCapture(captureDataUrl);
      const resolvedScenarioId = detectedScenarioId ?? scenarioId;

      setIsAnalyzing(true);
      window.setTimeout(() => {
        setIsAnalyzing(false);
        onCaptureComplete(captureDataUrl, "locked", resolvedScenarioId);
      }, 4000);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <section className="demo-screen camera-screen">
      <div className="camera-stage fullscreen-camera">
        <video ref={videoRef} muted playsInline className="camera-feed" />
        <div ref={guideRef} className="guide-43" aria-hidden="true">
          <div className="guide-label">4:3 alignment guide</div>
          {showLockedResult && scenario && lockedCaptureDataUrl ? (
            <div className="locked-guide-result">
              <img className="locked-guide-image" src={lockedCaptureDataUrl} alt="Captured guide frame" />
              <DemoOverlayRenderer overlays={scenario.overlays} paths={scenario.paths} scenarioId={scenarioId} />
            </div>
          ) : null}
        </div>
        {isAnalyzing ? (
          <div className="analyzing-overlay" aria-live="polite">
            <div className="sweep-line" />
            <p>Locking spatial anchors</p>
            <p className="secondary">{analyzeSteps[analyzeStep]}</p>
          </div>
        ) : null}

        <div className="camera-overlay-ui">
          <div className="scenario-strip overlay-strip">
            {scenarioButtons.map((button) => (
              <button
                key={button.id}
                type="button"
                className={`scenario-pill ${scenarioId === button.id ? "active" : ""}`}
                onClick={() => onSelectScenario(button.id)}
                disabled={isAnalyzing}
              >
                {button.label}
              </button>
            ))}
          </div>

          <div className="camera-topbar overlay-topbar">
            <div>
              <h2>{scenario?.title ?? (scenarioId === "math" ? MATH_BASELINE_COPY.title : FREE_SCAN_COPY.title)}</h2>
              <p>
                {scenarioId === "free"
                  ? "Capture any scene. This mode does not project deterministic overlays."
                  : scenarioId === "math"
                    ? "Original capture-first flow. Use scenario buttons only when you want overlays."
                    : "Point your phone at the matching scene image and fill the guide."}
              </p>
            </div>
          </div>

          <div className="camera-actions overlay-actions">
            {showLockedResult && scenario ? (
              <>
                <button type="button" className="ghost-btn" onClick={onExitLockedResult}>
                  Clear AR Lock
                </button>
                <button type="button" className="primary-btn" onClick={handleCapture} disabled={!cameraReady || isAnalyzing}>
                  Capture Again
                </button>
              </>
            ) : (
              <button type="button" className="primary-btn" onClick={handleCapture} disabled={!cameraReady || isAnalyzing}>
                {scenarioId === "free" || scenarioId === "math" ? "Capture Photo" : "Capture & Analyze"}
              </button>
            )}
          </div>

          {error ? <p className="camera-error overlay-error">Camera error: {error}</p> : null}
        </div>
      </div>
    </section>
  );
}

