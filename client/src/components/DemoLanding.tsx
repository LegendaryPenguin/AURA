import type { DemoScenarioId } from "../data/demoScenarios";

interface DemoLandingProps {
  onSelect: (scenarioId: DemoScenarioId) => void;
}

const cards: Array<{ id: DemoScenarioId; title: string; description: string }> = [
  {
    id: "care",
    title: "Care Safety Scan",
    description: "Medication and caregiver safety workflow.",
  },
  {
    id: "sustainability",
    title: "Sustainability Audit",
    description: "Energy and waste action checklist.",
  },
  {
    id: "wayfinding",
    title: "Wayfinding Assistant",
    description: "Accessible route and obstacle guidance.",
  },
  {
    id: "free",
    title: "Take Photo / Free Scan",
    description: "Capture a scene without simulated analysis.",
  },
];

export function DemoLanding({ onSelect }: DemoLandingProps) {
  return (
    <section className="demo-screen landing-screen">
      <div className="aurora-bg" aria-hidden="true" />
      <header className="landing-header">
        <h1>AURA</h1>
        <p className="subtitle">Edge Spatial Intelligence Demo</p>
        <p className="note">Choose a scenario, point your phone at the displayed scene, and capture.</p>
      </header>

      <div className="scenario-grid">
        {cards.map((card) => (
          <button
            type="button"
            key={card.id}
            className={`scenario-card scenario-${card.id}`}
            onClick={() => onSelect(card.id)}
          >
            <span className="scenario-title">{card.title}</span>
            <span className="scenario-description">{card.description}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

