import { useMemo, useState } from "react";
import { DemoCamera } from "./components/DemoCamera";
import { DemoResult } from "./components/DemoResult";
import { DEMO_SCENARIOS, type DemoScenarioId } from "./data/demoScenarios";
import "./styles/demo.css";

type DemoStage = "camera" | "result";

export default function App() {
  const [stage, setStage] = useState<DemoStage>("camera");
  const [activeScenarioId, setActiveScenarioId] = useState<DemoScenarioId>("math");
  const [capturedDataUrl, setCapturedDataUrl] = useState<string | null>(null);
  const [lockedScenarioPreview, setLockedScenarioPreview] = useState(false);

  const scenario = useMemo(
    () => (activeScenarioId === "free" || activeScenarioId === "math" ? undefined : DEMO_SCENARIOS[activeScenarioId]),
    [activeScenarioId],
  );

  if (stage === "camera") {
    return (
      <DemoCamera
        scenarioId={activeScenarioId}
        scenario={scenario}
        showLockedResult={lockedScenarioPreview}
        lockedCaptureDataUrl={capturedDataUrl}
        onExitLockedResult={() => {
          setLockedScenarioPreview(false);
          setCapturedDataUrl(null);
        }}
        onSelectScenario={(scenarioId) => {
          setActiveScenarioId(scenarioId);
          setLockedScenarioPreview(false);
          setCapturedDataUrl(null);
        }}
        onCaptureComplete={(dataUrl, target = "result", detectedScenarioId) => {
          if (detectedScenarioId) {
            setActiveScenarioId(detectedScenarioId);
          }
          setCapturedDataUrl(dataUrl);
          if (target === "locked") {
            setLockedScenarioPreview(true);
            return;
          }
          setLockedScenarioPreview(false);
          setStage("result");
        }}
      />
    );
  }

  return (
    <DemoResult
      scenarioId={activeScenarioId}
      scenario={scenario}
      capturedDataUrl={capturedDataUrl ?? ""}
      onBackToHome={() => {
        setCapturedDataUrl(null);
        setStage("camera");
      }}
    />
  );
}
