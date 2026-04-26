import { useEffect, useMemo, useState } from "react";
import { DemoOverlayRenderer } from "./DemoOverlayRenderer";
import { FREE_SCAN_COPY, MATH_BASELINE_COPY, type DemoScenario, type DemoScenarioId } from "../data/demoScenarios";

interface DemoResultProps {
  scenarioId: DemoScenarioId;
  scenario?: DemoScenario;
  capturedDataUrl: string;
  onBackToHome: () => void;
}

export function DemoResult({ scenarioId, scenario, capturedDataUrl, onBackToHome }: DemoResultProps) {
  const [useReferenceImage, setUseReferenceImage] = useState(false);
  const [referenceBroken, setReferenceBroken] = useState(false);
  const [mathStage, setMathStage] = useState<0 | 1 | 2 | 3>(0);
  const isFreeScan = scenarioId === "free" || scenarioId === "math";
  const overlayCount = scenario?.overlays.length ?? 0;

  useEffect(() => {
    if (scenarioId !== "math") {
      return;
    }
    setMathStage(0);
    const timers = [
      window.setTimeout(() => setMathStage(1), 450),
      window.setTimeout(() => setMathStage(2), 1200),
      window.setTimeout(() => setMathStage(3), 2050),
    ];
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [scenarioId, capturedDataUrl]);

  const backgroundImage = useMemo(() => {
    if (!isFreeScan && useReferenceImage && scenario?.referenceImagePath && !referenceBroken) {
      return scenario.referenceImagePath;
    }
    return capturedDataUrl;
  }, [capturedDataUrl, isFreeScan, referenceBroken, scenario?.referenceImagePath, useReferenceImage]);

  return (
    <section className="demo-screen result-screen">
      <div className="result-stage">
        {scenarioId === "math" ? (
          <div className="math-split">
            <div className="math-pane">
              <p className="math-pane-title">Captured Frame</p>
              <img className="result-image" src={capturedDataUrl} alt="Captured scene" />
            </div>
            <div className="math-pane">
              <p className="math-pane-title">Tutor Video Render</p>
              {mathStage < 3 ? (
                <div className="math-processing">
                  <p className={mathStage >= 1 ? "done" : ""}>1) Extracting handwritten steps</p>
                  <p className={mathStage >= 2 ? "done" : ""}>2) Running correction + final check</p>
                  <p className={mathStage >= 3 ? "done" : ""}>3) Rendering tutorial scene</p>
                </div>
              ) : (
                <video
                  className="math-video"
                  src="https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"
                  autoPlay
                  loop
                  muted
                  playsInline
                />
              )}
            </div>
          </div>
        ) : (
          <img className="result-image" src={backgroundImage} alt="Captured scene" />
        )}
        {!isFreeScan && scenario ? (
          <div className="result-overlay-viewport">
            <DemoOverlayRenderer overlays={scenario.overlays} paths={scenario.paths} />
          </div>
        ) : null}
        <div className="result-scanline" aria-hidden="true" />
      </div>

      <div className="result-top-panel">
        <h2>{scenario?.title ?? (scenarioId === "math" ? MATH_BASELINE_COPY.title : FREE_SCAN_COPY.title)}</h2>
        <p>{scenario?.summary ?? (scenarioId === "math" ? MATH_BASELINE_COPY.neutralMessage : FREE_SCAN_COPY.neutralMessage)}</p>
        <div className="chips">
          <span className="chip">Local demo mode</span>
          <span className="chip">Overlays: {overlayCount}</span>
          {scenario?.impactScore ? <span className="chip">Impact Score: {scenario.impactScore}</span> : null}
        </div>
      </div>

      <div className="status-log">
        {scenarioId === "math" ? (
          <>
            <p>[AURA-MATH] Snapshot received.</p>
            <p>[AURA-MATH] OCR pipeline {mathStage >= 1 ? "complete" : "running"}.</p>
            <p>[AURA-MATH] Correction pass {mathStage >= 2 ? "complete" : "queued"}.</p>
            <p>[AURA-MATH] Video render {mathStage >= 3 ? "ready" : "in progress"}.</p>
          </>
        ) : (
          <>
            <p>[AURA] Frame stabilized.</p>
            <p>[AURA] Spatial anchors locked.</p>
            <p>[AURA] Overlay projection complete.</p>
          </>
        )}
      </div>

      <div className="result-bottom-panel">
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

