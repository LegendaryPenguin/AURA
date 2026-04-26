import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { DemoOverlayRenderer } from "./DemoOverlayRenderer";
import { FREE_SCAN_COPY, MATH_BASELINE_COPY, type DemoScenario, type DemoScenarioId } from "../data/demoScenarios";
import { createVideoSimJob, getVideoSimJob, getVideoSimVideoUrl } from "../services/api";

interface DemoResultProps {
  scenarioId: DemoScenarioId;
  scenario?: DemoScenario;
  capturedDataUrl: string;
  onBackToHome: () => void;
}

export function DemoResult({ scenarioId, scenario, capturedDataUrl, onBackToHome }: DemoResultProps) {
  const mathBackgroundVideoRef = useRef<HTMLVideoElement | null>(null);
  const mathBackgroundStreamRef = useRef<MediaStream | null>(null);
  const mathGenerationStartRef = useRef<number>(0);
  const [useReferenceImage, setUseReferenceImage] = useState(false);
  const [referenceBroken, setReferenceBroken] = useState(false);
  const [mathJobStatus, setMathJobStatus] = useState<"idle" | "queued" | "running" | "done" | "error">("idle");
  const [mathStatusMessage, setMathStatusMessage] = useState("Ready to generate video.");
  const [mathVideoUrl, setMathVideoUrl] = useState("");
  const [mathVideoVisible, setMathVideoVisible] = useState(false);
  const [mathBackgroundLive, setMathBackgroundLive] = useState(false);
  const [mathArReleased, setMathArReleased] = useState(false);
  const [parallax, setParallax] = useState({ x: 0, y: 0 });
  const isMath = scenarioId === "math";
  const isFreeScan = scenarioId === "free";
  const overlayCount = scenario?.overlays.length ?? 0;
  const backupMathVideoUrl = "/videos/tutorial_animation_20260426_002557.mp4";

  useEffect(() => {
    if (!isMath) {
      return;
    }
    setMathJobStatus("idle");
    setMathStatusMessage("Ready to generate video.");
    setMathVideoUrl("");
    setMathVideoVisible(false);
    setMathArReleased(false);
  }, [isMath, capturedDataUrl]);

  useEffect(() => {
    if (!isMath || mathJobStatus !== "idle") {
      return;
    }
    void runMathGeneration();
    // Intentionally depends on status + scenario only to auto-run once per capture reset.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isMath, mathJobStatus]);

  useEffect(() => {
    if (!isMath || mathArReleased) {
      setMathBackgroundLive(false);
      if (mathBackgroundVideoRef.current) {
        mathBackgroundVideoRef.current.pause();
        mathBackgroundVideoRef.current.srcObject = null;
      }
      if (mathBackgroundStreamRef.current) {
        mathBackgroundStreamRef.current.getTracks().forEach((track) => track.stop());
        mathBackgroundStreamRef.current = null;
      }
      return;
    }

    const startBackgroundCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } },
          audio: false,
        });
        mathBackgroundStreamRef.current = stream;
        if (mathBackgroundVideoRef.current) {
          mathBackgroundVideoRef.current.srcObject = stream;
          await mathBackgroundVideoRef.current.play();
          setMathBackgroundLive(true);
        }
      } catch {
        setMathBackgroundLive(false);
      }
    };

    void startBackgroundCamera();

    return () => {
      if (mathBackgroundVideoRef.current) {
        mathBackgroundVideoRef.current.pause();
        mathBackgroundVideoRef.current.srcObject = null;
      }
      if (mathBackgroundStreamRef.current) {
        mathBackgroundStreamRef.current.getTracks().forEach((track) => track.stop());
        mathBackgroundStreamRef.current = null;
      }
    };
  }, [isMath, mathArReleased]);

  const backgroundImage = useMemo(() => {
    if (!isMath && !isFreeScan && useReferenceImage && scenario?.referenceImagePath && !referenceBroken) {
      return scenario.referenceImagePath;
    }
    return capturedDataUrl;
  }, [capturedDataUrl, isMath, isFreeScan, referenceBroken, scenario?.referenceImagePath, useReferenceImage]);

  const handleParallaxMove = (clientX: number, clientY: number, stage: HTMLDivElement | null) => {
    if (!stage || isFreeScan || isMath) {
      return;
    }
    const rect = stage.getBoundingClientRect();
    if (!rect.width || !rect.height) {
      return;
    }
    const nx = (clientX - rect.left) / rect.width - 0.5;
    const ny = (clientY - rect.top) / rect.height - 0.5;
    setParallax({
      x: Math.max(-1, Math.min(1, nx)) * 10,
      y: Math.max(-1, Math.min(1, ny)) * 10,
    });
  };

  const dataUrlToBlob = async (dataUrl: string): Promise<Blob> => {
    const response = await fetch(dataUrl);
    return response.blob();
  };

  const runMathGeneration = async () => {
    if (mathJobStatus === "queued" || mathJobStatus === "running") {
      return;
    }
    const minVideoRevealMs = 4500;
    mathGenerationStartRef.current = Date.now();
    const finalizeMathVideo = async (videoUrl: string, message: string) => {
      const elapsed = Date.now() - mathGenerationStartRef.current;
      const remaining = Math.max(0, minVideoRevealMs - elapsed);
      if (remaining > 0) {
        await new Promise((resolve) => window.setTimeout(resolve, remaining));
      }
      setMathVideoVisible(false);
      setMathVideoUrl(videoUrl);
      setMathJobStatus("done");
      setMathStatusMessage(message);
    };

    setMathVideoUrl(backupMathVideoUrl);
    setMathJobStatus("queued");
    setMathStatusMessage("Uploading photo...");

    try {
      const captureBlob = await dataUrlToBlob(capturedDataUrl);
      const create = await createVideoSimJob(captureBlob);
      const jobId = create.job_id;
      setMathJobStatus("running");
      setMathStatusMessage("Generating video...");

      let attempts = 0;
      const maxAttempts = 60;
      while (attempts < maxAttempts) {
        await new Promise((resolve) => window.setTimeout(resolve, 1200));
        const state = await getVideoSimJob(jobId);
        if (state.message) {
          setMathStatusMessage(state.message);
        }
        if (state.status === "done") {
          await finalizeMathVideo(getVideoSimVideoUrl(jobId), "video_ready");
          return;
        }
        if (state.status === "error") {
          await finalizeMathVideo(
            backupMathVideoUrl,
            state.error || state.message || "Generation failed. Using backup video.",
          );
          return;
        }
        attempts += 1;
      }
      await finalizeMathVideo(backupMathVideoUrl, "Generation timed out. Using backup video.");
    } catch (error) {
      await finalizeMathVideo(backupMathVideoUrl, (error as Error).message || "Generation failed. Using backup video.");
    }
  };

  return (
    <section className="demo-screen result-screen">
      <div
        className="result-stage"
        onMouseMove={(event) => handleParallaxMove(event.clientX, event.clientY, event.currentTarget)}
        onMouseLeave={() => setParallax({ x: 0, y: 0 })}
        onTouchMove={(event) => {
          const touch = event.touches[0];
          if (touch) {
            handleParallaxMove(touch.clientX, touch.clientY, event.currentTarget);
          }
        }}
        onTouchEnd={() => setParallax({ x: 0, y: 0 })}
      >
        {isMath ? (
          <>
            {!mathArReleased ? <video ref={mathBackgroundVideoRef} className="math-live-bg" muted playsInline /> : null}
            {!mathBackgroundLive || mathArReleased ? <img className="result-image" src={capturedDataUrl} alt="Captured scene" /> : null}
          </>
        ) : (
          <img className="result-image" src={backgroundImage} alt="Captured scene" />
        )}
        {isMath ? (
          <div className="math-video-overlay">
            <div className="math-pane">
              {mathJobStatus === "done" ? (
                <video
                  className={`math-video ${mathVideoVisible ? "visible" : ""}`}
                  src={mathVideoUrl}
                  autoPlay
                  loop
                  muted
                  playsInline
                  disablePictureInPicture
                  controlsList="nodownload noplaybackrate noremoteplayback"
                  onLoadedData={() => setMathVideoVisible(true)}
                  onError={() => {
                    setMathJobStatus("done");
                    setMathStatusMessage("Generated video unavailable. Using backup video.");
                    setMathVideoUrl(backupMathVideoUrl);
                    setMathVideoVisible(false);
                  }}
                />
              ) : null}
              {!mathVideoVisible ? <div className="math-processing minimal" aria-label="Generating tutor video" /> : null}
            </div>
          </div>
        ) : null}
        {!isMath && !isFreeScan && scenario ? (
          <div
            className="result-overlay-viewport"
            style={
              {
                "--parallax-x": `${parallax.x}px`,
                "--parallax-y": `${parallax.y}px`,
              } as CSSProperties
            }
          >
            <div className={`ar-field ar-field-${scenarioId}`} aria-hidden="true" />
            <DemoOverlayRenderer
              overlays={scenario.overlays}
              paths={scenario.paths}
              scenarioId={scenarioId}
              monitorRoutes={scenario.monitorRoutes}
              monitorDestinations={scenario.monitorDestinations}
            />
          </div>
        ) : null}
        <div className={`result-scanline ${scenarioId === "sustainability" ? "monitor-soft" : ""}`} aria-hidden="true" />
        {!isMath ? (
          <div className="result-top-panel overlay-panel">
            <h2>{scenario?.title ?? FREE_SCAN_COPY.title}</h2>
            <p>{scenario?.summary ?? FREE_SCAN_COPY.neutralMessage}</p>
            <div className="chips">
              <span className="chip">Local demo mode</span>
              <span className="chip">Overlays: {overlayCount}</span>
              {scenario?.impactScore ? <span className="chip">Impact Score: {scenario.impactScore}</span> : null}
            </div>
          </div>
        ) : null}

        {!isMath ? (
          <div className="status-log overlay-panel status-floating">
            <p>[AURA] Frame stabilized.</p>
            <p>[AURA] Spatial anchors locked.</p>
            <p>[AURA] Overlay projection complete.</p>
          </div>
        ) : null}

        <div className={`result-bottom-panel overlay-panel${isMath ? " math-bottom-minimal" : ""}`}>
          {!isMath && !isFreeScan && scenario ? (
            <>
              <p className="panel-title">Action Panel • {scenario.actionAgent}</p>
              <p>{scenario.actionText}</p>
              <p className="panel-secondary">{scenario.handoffText}</p>
              <div className="badge-row">
                {scenario.badges.map((badge) => (
                  <span key={badge} className="badge">
                    {badge}
                  </span>
                ))}
              </div>
            </>
          ) : isMath ? null : (
            <p>{FREE_SCAN_COPY.neutralMessage}</p>
          )}
          {!isMath && !isFreeScan && overlayCount === 0 ? <p>No scenario overlays selected.</p> : null}
          {isMath ? (
            <div className="math-bottom-actions">
              <button
                type="button"
                className="ghost-btn"
                onClick={() => setMathArReleased((prev) => !prev)}
              >
                {mathArReleased ? "Enable AR" : "Release AR"}
              </button>
              <button type="button" className="primary-btn" onClick={onBackToHome}>
                Back to Camera
              </button>
            </div>
          ) : (
            <button type="button" className="primary-btn" onClick={onBackToHome}>
              Reset / Back
            </button>
          )}
        </div>
      </div>

      {!isMath && !isFreeScan && scenario?.referenceImagePath ? (
        <div className="dev-tools">
          <button type="button" onClick={() => setUseReferenceImage((prev) => !prev)} className="dev-btn">
            {useReferenceImage ? "Use captured image" : "Use reference image"}
          </button>
          <img
            src={scenario.referenceImagePath}
            alt=""
            style={{ display: "none" }}
            onError={() => setReferenceBroken(true)}
          />
        </div>
      ) : null}
    </section>
  );
}

