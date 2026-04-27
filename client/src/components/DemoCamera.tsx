import { useEffect, useMemo, useRef, useState } from "react";
import { DemoOverlayRenderer } from "./DemoOverlayRenderer";
import type { DemoScenario, DemoScenarioId } from "../data/demoScenarios";
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
  { id: "math", label: "Inform" },
  { id: "care", label: "Simulate" },
  { id: "sustainability", label: "Monitor" },
  { id: "wayfinding", label: "Guide" },
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
  const [monitorOverlayBroken, setMonitorOverlayBroken] = useState(false);

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
        const message = (err as Error).message || "Unable to open camera";
        if (message.toLowerCase().includes("aborted")) {
          setError(null);
          return;
        }
        setError(message);
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

  useEffect(() => {
    setError(null);
  }, [scenarioId, showLockedResult]);

  useEffect(() => {
    setMonitorOverlayBroken(false);
  }, [scenarioId, showLockedResult, lockedCaptureDataUrl]);

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
      if (scenarioId === "math") {
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
      const message = (err as Error).message || "Capture failed. Try again.";
      if (message.toLowerCase().includes("aborted")) {
        setError(null);
        return;
      }
      setError(message);
    }
  };

  return (
    <section className="demo-screen camera-screen">
      <div className="camera-stage fullscreen-camera">
        <video ref={videoRef} muted playsInline className="camera-feed" />
        <div ref={guideRef} className="guide-43" aria-hidden="true">
          {showLockedResult && scenario && lockedCaptureDataUrl ? (
            <div className="locked-guide-result">
              <img className="locked-guide-image" src={lockedCaptureDataUrl} alt="Captured guide frame" />
              {scenarioId === "sustainability" ? (
                !monitorOverlayBroken ? (
                  <img
                    className="monitor-fix-overlay"
                    src={scenario.referenceImagePath ?? "/demo-scenes/sustainability2.0.png"}
                    alt=""
                    onError={() => setMonitorOverlayBroken(true)}
                  />
                ) : null
              ) : (
                <DemoOverlayRenderer
                  overlays={scenario.overlays}
                  paths={scenario.paths}
                  scenarioId={scenarioId}
                  variant="locked"
                  monitorRoutes={scenario.monitorRoutes}
                  monitorDestinations={scenario.monitorDestinations}
                />
              )}
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

          {/* Top instructional copy removed to keep UI clean behind mode buttons. */}

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
                {scenarioId === "math" ? "Capture Photo" : "Capture & Analyze"}
              </button>
            )}
          </div>

          {error ? <p className="camera-error overlay-error">Camera error: {error}</p> : null}
        </div>
      </div>
    </section>
  );
}

