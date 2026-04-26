export type DemoScenarioId = "math" | "care" | "sustainability" | "wayfinding" | "free";

export type OverlaySeverity = "High" | "Medium" | "Low" | "Positive" | "Route";

export interface OverlayBox {
  id: string;
  label: string;
  confidence: number;
  severity: OverlaySeverity;
  x: number;
  y: number;
  width: number;
  height: number;
  chip?: string;
}

export interface OverlayPath {
  id: string;
  label: string;
  confidence: number;
  severity: OverlaySeverity;
  points: Array<{ x: number; y: number }>;
}

export interface DemoScenario {
  id: DemoScenarioId;
  title: string;
  subtitle: string;
  description: string;
  summary: string;
  runtimeBadge: string;
  actionAgent: string;
  actionText: string;
  handoffText: string;
  badges: string[];
  impactScore?: string;
  referenceImagePath?: string;
  overlays: OverlayBox[];
  paths?: OverlayPath[];
}

export const DEMO_SCENARIOS: Record<Exclude<DemoScenarioId, "free" | "math">, DemoScenario> = {
  care: {
    id: "care",
    title: "Care Safety Scan",
    subtitle: "Medication and caregiver safety workflow.",
    description: "Point your phone at the care scene and capture to project deterministic AURA overlays.",
    summary: "AURA detected a medication safety workflow.",
    runtimeBadge: "Local demo mode",
    actionAgent: "CareAgent",
    actionText: "Verify dosage before use.",
    handoffText: "Prepare caregiver notification if unresolved.",
    badges: ["Catalyst for Care", "Social Impact", "Edge AI"],
    referenceImagePath: "/demo-scenes/medical1.png",
    overlays: [
      {
        id: "med-bottle",
        label: "Verify dosage before taking",
        confidence: 96,
        severity: "High",
        x: 0.46,
        y: 0.36,
        width: 0.12,
        height: 0.26,
      },
      {
        id: "pill-org",
        label: "Missed dose risk",
        confidence: 93,
        severity: "High",
        x: 0.18,
        y: 0.56,
        width: 0.34,
        height: 0.22,
      },
      {
        id: "water",
        label: "Hydration reminder",
        confidence: 89,
        severity: "Medium",
        x: 0.62,
        y: 0.28,
        width: 0.13,
        height: 0.34,
      },
      {
        id: "phone",
        label: "Caregiver alert available",
        confidence: 87,
        severity: "Medium",
        x: 0.58,
        y: 0.63,
        width: 0.18,
        height: 0.2,
        chip: "handoff available",
      },
      {
        id: "notepad",
        label: "Check written instructions",
        confidence: 82,
        severity: "Low",
        x: 0.08,
        y: 0.34,
        width: 0.2,
        height: 0.16,
      },
    ],
  },
  sustainability: {
    id: "sustainability",
    title: "Sustainability Audit",
    subtitle: "Energy and waste action checklist.",
    description: "Capture the sustainability scene to reveal deterministic room-level actions.",
    summary: "AURA detected room-level sustainability actions.",
    runtimeBadge: "Local demo mode",
    actionAgent: "EcoAgent",
    actionText: "Create a 3-step sustainability checklist.",
    handoffText: "Save audit report.",
    badges: ["Sustain the Spark", "Social Impact", "Edge AI"],
    impactScore: "74/100",
    referenceImagePath: "/demo-scenes/sustainability2.png",
    overlays: [
      {
        id: "power-strip",
        label: "Idle energy draw detected",
        confidence: 94,
        severity: "High",
        x: 0.52,
        y: 0.63,
        width: 0.3,
        height: 0.17,
      },
      {
        id: "food-container",
        label: "Compost or dispose properly",
        confidence: 91,
        severity: "Medium",
        x: 0.2,
        y: 0.55,
        width: 0.18,
        height: 0.18,
      },
      {
        id: "plastic-cup",
        label: "Recycle or reuse",
        confidence: 88,
        severity: "Medium",
        x: 0.43,
        y: 0.42,
        width: 0.11,
        height: 0.21,
      },
      {
        id: "lamp",
        label: "Turn off when leaving",
        confidence: 84,
        severity: "Low",
        x: 0.72,
        y: 0.18,
        width: 0.16,
        height: 0.34,
      },
      {
        id: "recycling-bin",
        label: "Correct disposal route",
        confidence: 97,
        severity: "Positive",
        x: 0.07,
        y: 0.52,
        width: 0.14,
        height: 0.31,
      },
    ],
  },
  wayfinding: {
    id: "wayfinding",
    title: "Wayfinding Assistant",
    subtitle: "Accessible route and obstacle guidance.",
    description: "Capture the hallway scene and project the route with deterministic overlays.",
    summary: "AURA detected a safe route through the hallway.",
    runtimeBadge: "Local demo mode",
    actionAgent: "NavigationAgent",
    actionText: "Continue forward and avoid the right-side obstacle.",
    handoffText: "Provide navigation cue.",
    badges: ["Light the Way", "Best UI/UX", "Social Impact"],
    referenceImagePath: "/demo-scenes/wayfinding3.png",
    overlays: [
      {
        id: "exit-door",
        label: "Destination detected",
        confidence: 92,
        severity: "Positive",
        x: 0.42,
        y: 0.15,
        width: 0.2,
        height: 0.29,
      },
      {
        id: "chair-obstacle",
        label: "Avoid right-side obstruction",
        confidence: 90,
        severity: "Medium",
        x: 0.69,
        y: 0.54,
        width: 0.18,
        height: 0.3,
      },
      {
        id: "open-path",
        label: "Continue forward",
        confidence: 88,
        severity: "Route",
        x: 0.33,
        y: 0.48,
        width: 0.26,
        height: 0.43,
      },
      {
        id: "landmark",
        label: "Orientation landmark",
        confidence: 81,
        severity: "Low",
        x: 0.16,
        y: 0.3,
        width: 0.1,
        height: 0.2,
      },
    ],
    paths: [
      {
        id: "route-main",
        label: "Safer path forward",
        confidence: 95,
        severity: "Route",
        points: [
          { x: 0.5, y: 0.92 },
          { x: 0.51, y: 0.78 },
          { x: 0.52, y: 0.64 },
          { x: 0.5, y: 0.5 },
          { x: 0.52, y: 0.35 },
          { x: 0.52, y: 0.23 },
        ],
      },
    ],
  },
};

export const FREE_SCAN_COPY = {
  title: "Take Photo / Free Scan",
  subtitle: "Capture a scene without simulated analysis.",
  neutralMessage:
    "Scene captured. Choose Care, Sustainability, or Wayfinding for the full AURA scenario workflow.",
};

export const MATH_BASELINE_COPY = {
  title: "Math Baseline Capture",
  subtitle: "Original capture-first demo flow.",
  neutralMessage: "Scene captured in baseline mode. Select a scenario only when you want deterministic overlays.",
};

