import { useMemo, useState } from "react";
import { AuraHome } from "./components/AuraHome";
import { DemoCamera } from "./components/DemoCamera";
import { DemoResult } from "./components/DemoResult";
import { DEMO_SCENARIOS, type DemoScenarioId } from "./data/demoScenarios";
import "./styles/demo.css";

type DemoStage = "home" | "camera" | "result";

export default function App() {
  const [stage, setStage] = useState<DemoStage>("home");
  const [homeExiting, setHomeExiting] = useState(false);
  const [activeScenarioId, setActiveScenarioId] = useState<DemoScenarioId>("math");
  const [capturedDataUrl, setCapturedDataUrl] = useState<string | null>(null);
  const [lockedScenarioPreview, setLockedScenarioPreview] = useState(false);

  const scenario = useMemo(
    () => (activeScenarioId === "free" || activeScenarioId === "math" ? undefined : DEMO_SCENARIOS[activeScenarioId]),
    [activeScenarioId],
  );

  if (stage === "home") {
    return (
      <AuraHome
        isExiting={homeExiting}
        onLaunch={() => {
          if (homeExiting) {
            return;
          }
          setHomeExiting(true);
          window.setTimeout(() => {
            setStage("camera");
            setHomeExiting(false);
          }, 280);
        }}
      />
    );
  }

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
