import { useEffect, useMemo, useState, type CSSProperties } from "react";
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
  const [useReferenceImage, setUseReferenceImage] = useState(false);
  const [referenceBroken, setReferenceBroken] = useState(false);
  const [mathJobStatus, setMathJobStatus] = useState<"idle" | "queued" | "running" | "done" | "error">("idle");
  const [mathStatusMessage, setMathStatusMessage] = useState("Ready to generate video.");
  const [mathVideoUrl, setMathVideoUrl] = useState("");
  const [parallax, setParallax] = useState({ x: 0, y: 0 });
  const isFreeScan = scenarioId === "free" || scenarioId === "math";
  const overlayCount = scenario?.overlays.length ?? 0;
  const backupMathVideoUrl = "/videos/tutorial_animation_20260426_002557.mp4";

  useEffect(() => {
    if (scenarioId !== "math") {
      return;
    }
    setMathJobStatus("idle");
    setMathStatusMessage("Ready to generate video.");
    setMathVideoUrl("");
  }, [scenarioId, capturedDataUrl]);

  const backgroundImage = useMemo(() => {
    if (!isFreeScan && useReferenceImage && scenario?.referenceImagePath && !referenceBroken) {
      return scenario.referenceImagePath;
    }
    return capturedDataUrl;
  }, [capturedDataUrl, isFreeScan, referenceBroken, scenario?.referenceImagePath, useReferenceImage]);

  const handleParallaxMove = (clientX: number, clientY: number, stage: HTMLDivElement | null) => {
    if (!stage || isFreeScan) {
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
          setMathVideoUrl(getVideoSimVideoUrl(jobId));
          setMathJobStatus("done");
          setMathStatusMessage("video_ready");
          return;
        }
        if (state.status === "error") {
          setMathVideoUrl(backupMathVideoUrl);
          setMathJobStatus("done");
          setMathStatusMessage(state.error || state.message || "Generation failed. Using backup video.");
          return;
        }
        attempts += 1;
      }
      setMathVideoUrl(backupMathVideoUrl);
      setMathJobStatus("done");
      setMathStatusMessage("Generation timed out. Using backup video.");
    } catch (error) {
      setMathVideoUrl(backupMathVideoUrl);
      setMathJobStatus("done");
      setMathStatusMessage((error as Error).message || "Generation failed. Using backup video.");
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
        {scenarioId === "math" ? (
          <div className="math-split-overlay">
            <div className="math-pane">
              <p className="math-pane-title">Captured Frame</p>
              <img className="result-image" src={capturedDataUrl} alt="Captured scene" />
            </div>
            <div className="math-pane">
              <p className="math-pane-title">Tutor Video Render</p>
              {mathJobStatus !== "done" ? (
                <div className="math-processing stacked">
                  <p className={mathJobStatus !== "idle" ? "done" : ""}>Snapshot received.</p>
                  <p className={mathJobStatus === "running" ? "done" : ""}>Transcribing and correcting steps.</p>
                  <p>Rendering tutorial scene.</p>
                  <button type="button" className="primary-btn math-generate-btn" onClick={runMathGeneration}>
                    {mathJobStatus === "idle" || mathJobStatus === "error"
                      ? "Generate video"
                      : "Generating..."}
                  </button>
                  <p className="math-status">Status: {mathStatusMessage}</p>
                </div>
              ) : (
                <video
                  className="math-video"
                  src={mathVideoUrl}
                  autoPlay
                  loop
                  muted
                  playsInline
                  controls
                  onError={() => {
                    setMathJobStatus("done");
                    setMathStatusMessage("Generated video unavailable. Using backup video.");
                    setMathVideoUrl(backupMathVideoUrl);
                  }}
                />
              )}
            </div>
          </div>
        ) : (
          <img className="result-image" src={backgroundImage} alt="Captured scene" />
        )}
        {!isFreeScan && scenario ? (
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
            <DemoOverlayRenderer overlays={scenario.overlays} paths={scenario.paths} scenarioId={scenarioId} />
          </div>
        ) : null}
        <div className="result-scanline" aria-hidden="true" />
        <div className="result-top-panel overlay-panel">
          <h2>{scenario?.title ?? (scenarioId === "math" ? MATH_BASELINE_COPY.title : FREE_SCAN_COPY.title)}</h2>
          <p>{scenario?.summary ?? (scenarioId === "math" ? MATH_BASELINE_COPY.neutralMessage : FREE_SCAN_COPY.neutralMessage)}</p>
          <div className="chips">
            <span className="chip">Local demo mode</span>
            <span className="chip">Overlays: {overlayCount}</span>
            {scenario?.impactScore ? <span className="chip">Impact Score: {scenario.impactScore}</span> : null}
          </div>
        </div>

        <div className="status-log overlay-panel status-floating">
          {scenarioId === "math" ? (
            <>
              <p>[AURA-MATH] Snapshot received.</p>
              <p>[AURA-MATH] Job status: {mathJobStatus}.</p>
              <p>[AURA-MATH] {mathStatusMessage}</p>
              <p>[AURA-MATH] Output: {mathJobStatus === "done" ? "backup video ready" : "pending"}.</p>
            </>
          ) : (
            <>
              <p>[AURA] Frame stabilized.</p>
              <p>[AURA] Spatial anchors locked.</p>
              <p>[AURA] Overlay projection complete.</p>
            </>
          )}
        </div>

        <div className="result-bottom-panel overlay-panel">
          {!isFreeScan && scenario ? (
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
          ) : (
            <p>{scenarioId === "math" ? MATH_BASELINE_COPY.neutralMessage : FREE_SCAN_COPY.neutralMessage}</p>
          )}
          {!isFreeScan && overlayCount === 0 ? <p>No scenario overlays selected.</p> : null}
          <button type="button" className="primary-btn" onClick={onBackToHome}>
            Reset / Back
          </button>
        </div>
      </div>

      {!isFreeScan && scenario?.referenceImagePath ? (
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

