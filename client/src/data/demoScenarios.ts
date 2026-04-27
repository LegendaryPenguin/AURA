export type DemoScenarioId = "math" | "care" | "sustainability" | "wayfinding" | "free";

export type OverlaySeverity = "High" | "Medium" | "Low" | "Positive" | "Route";

export interface OverlayBox {
  id: string;
  label: string;
  compactLabel?: string;
  markerX?: number;
  markerY?: number;
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

export type MonitorRouteTarget = "recycle" | "trash";

export interface MonitorRouteItem {
  id: string;
  overlayId: string;
  label: string;
  target: MonitorRouteTarget;
  destination: { x: number; y: number };
  points?: Array<{ x: number; y: number }>;
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
  monitorRoutes?: MonitorRouteItem[];
  monitorDestinations?: Array<{
    id: string;
    label: string;
    target: MonitorRouteTarget;
    x: number;
    y: number;
  }>;
}

export const DEMO_SCENARIOS: Record<Exclude<DemoScenarioId, "free" | "math">, DemoScenario> = {
  care: {
    id: "care",
    title: "Care Safety Scan",
    subtitle: "Medication and caregiver safety workflow.",
    description: "Point your phone at the care scene and capture to project deterministic AURA overlays.",
    summary: "AURA surfaced medication, hydration, and reminder readiness cues.",
    runtimeBadge: "Local demo mode",
    actionAgent: "CareAgent",
    actionText: "Confirm dosage details before taking medicine.",
    handoffText: "Prepare caregiver notification if unresolved.",
    badges: ["Catalyst for Care", "Social Impact", "Edge AI"],
    referenceImagePath: "/demo-scenes/medical1.png",
    overlays: [
      {
        id: "med-bottle",
        label: "Daily dosage: 1x Metformin, 2x Aspirin",
        compactLabel: "Daily dosage",
        markerX: 0.08,
        markerY: 0.46,
        confidence: 96,
        severity: "High",
        x: 0.38,
        y: 0.37,
        width: 0.08,
        height: 0.2,
      },
      {
        id: "water",
        label: "Water: 80% full",
        compactLabel: "Water 80% full",
        markerX: 0.84,
        markerY: 0.42,
        confidence: 89,
        severity: "Positive",
        x: 0.62,
        y: 0.28,
        width: 0.13,
        height: 0.34,
      },
      {
        id: "phone",
        label: "Reminder: Set alarm for 7:00",
        compactLabel: "Reminder: Set alarm for 7:00",
        markerX: 0.82,
        markerY: 0.68,
        confidence: 87,
        severity: "Positive",
        x: 0.58,
        y: 0.63,
        width: 0.18,
        height: 0.2,
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
    referenceImagePath: "/demo-scenes/sustainability2.0.png",
    overlays: [
      {
        id: "drink-cup",
        label: "Drink cup",
        compactLabel: "Drink cup",
        markerX: 0.24,
        markerY: 0.55,
        confidence: 93,
        severity: "Medium",
        x: 0.18,
        y: 0.45,
        width: 0.11,
        height: 0.19,
      },
      {
        id: "food-tray",
        label: "Food tray",
        compactLabel: "Food tray",
        markerX: 0.42,
        markerY: 0.64,
        confidence: 92,
        severity: "Medium",
        x: 0.28,
        y: 0.56,
        width: 0.24,
        height: 0.15,
      },
      {
        id: "bottle",
        label: "Bottle",
        compactLabel: "Bottle",
        markerX: 0.58,
        markerY: 0.42,
        confidence: 89,
        severity: "Medium",
        x: 0.52,
        y: 0.3,
        width: 0.1,
        height: 0.24,
      },
    ],
    monitorRoutes: [
      {
        id: "cup-recycle",
        overlayId: "drink-cup",
        label: "Drink cup",
        target: "recycle",
        destination: { x: 0.19, y: 0.71 },
        points: [
          { x: 0.11, y: 0.53 },
          { x: 0.2, y: 0.36 },
          { x: 0.36, y: 0.29 },
          { x: 0.55, y: 0.33 },
        ],
      },
      {
        id: "tray-trash",
        overlayId: "food-tray",
        label: "Food tray",
        target: "trash",
        destination: { x: 0.84, y: 0.58 },
        points: [
          { x: 0.35, y: 0.58 },
          { x: 0.58, y: 0.53 },
          { x: 0.75, y: 0.65 },
          { x: 0.86, y: 0.83 },
        ],
      },
      {
        id: "bottle-recycle",
        overlayId: "bottle",
        label: "Bottle",
        target: "trash",
        destination: { x: 0.85, y: 0.73 },
        points: [
          { x: 0.2, y: 0.46 },
          { x: 0.49, y: 0.45 },
          { x: 0.7, y: 0.5 },
          { x: 0.86, y: 0.76 },
        ],
      },
    ],
    monitorDestinations: [
      { id: "dest-recycle", label: "Recycle", target: "recycle", x: 0.19, y: 0.71 },
      { id: "dest-trash", label: "Trash", target: "trash", x: 0.74, y: 0.72 },
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

