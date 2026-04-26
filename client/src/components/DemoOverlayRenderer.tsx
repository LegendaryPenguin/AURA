import { useEffect, useMemo, useState, type CSSProperties } from "react";
import type { DemoScenarioId, MonitorRouteItem, OverlayBox, OverlayPath, OverlaySeverity } from "../data/demoScenarios";
import { WayfindingARLayer } from "./WayfindingARLayer";

interface DemoOverlayRendererProps {
  overlays: OverlayBox[];
  paths?: OverlayPath[];
  scenarioId: DemoScenarioId;
  variant?: "default" | "locked";
  monitorRoutes?: MonitorRouteItem[];
  monitorDestinations?: Array<{
    id: string;
    label: string;
    target: "recycle" | "trash";
    x: number;
    y: number;
  }>;
}

const severityClassMap: Record<OverlaySeverity, string> = {
  High: "sev-high",
  Medium: "sev-medium",
  Low: "sev-low",
  Positive: "sev-positive",
  Route: "sev-route",
};

function pathToSvg(points: Array<{ x: number; y: number }>): string {
  return points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x * 100} ${point.y * 100}`).join(" ");
}

function RoutePath({ path, index }: { path: OverlayPath; index: number }) {
  const d = useMemo(() => pathToSvg(path.points), [path.points]);
  return (
    <svg className="route-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
      <path
        d={d}
        className="route-path"
        style={{ animationDelay: `${index * 280 + 250}ms` }}
      />
      <circle
        className="route-arrowhead"
        cx={path.points[path.points.length - 1]?.x ? path.points[path.points.length - 1].x * 100 : 50}
        cy={path.points[path.points.length - 1]?.y ? path.points[path.points.length - 1].y * 100 : 50}
        r="1.8"
        style={{ animationDelay: `${index * 280 + 1100}ms` }}
      />
    </svg>
  );
}

function clampPercent(value: number, min = 3, max = 95): number {
  return Math.max(min, Math.min(max, value));
}

function clampUnit(value: number, min = 0.04, max = 0.96): number {
  return Math.max(min, Math.min(max, value));
}

function toAnchorPoint(overlay: OverlayBox): { x: number; y: number } {
  if (typeof overlay.markerX === "number" && typeof overlay.markerY === "number") {
    return { x: overlay.markerX, y: overlay.markerY };
  }
  return {
    x: overlay.x + overlay.width / 2,
    y: overlay.y + overlay.height / 2,
  };
}

function monitorRouteToSvgPath(
  source: { x: number; y: number },
  destination: { x: number; y: number },
  points?: Array<{ x: number; y: number }>,
): string {
  if (points && points.length >= 2) {
    return points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x * 100} ${point.y * 100}`).join(" ");
  }
  const sx = source.x * 100;
  const sy = source.y * 100;
  const dx = destination.x * 100;
  const dy = destination.y * 100;
  const cx = (sx + dx) / 2;
  const distanceY = Math.abs(sy - dy);
  const cy = Math.min(sy, dy) - Math.max(8, Math.min(16, distanceY * 0.35));
  return `M ${sx} ${sy} Q ${cx} ${cy} ${dx} ${dy}`;
}

function MonitorOverlayLayer({
  overlays,
  visibleCount,
  routes,
}: {
  visibleCount: number;
  routes: MonitorRouteItem[];
  overlays: OverlayBox[];
}) {
  const overlayById = useMemo(() => new Map(overlays.map((overlay) => [overlay.id, overlay])), [overlays]);
  const availableRoutes = useMemo(
    () =>
      routes
        .map((route) => {
          const overlay = overlayById.get(route.overlayId);
          if (!overlay) {
            return null;
          }
          const source = toAnchorPoint(overlay);
          return {
            ...route,
            source: { x: clampUnit(source.x), y: clampUnit(source.y) },
            destination: {
              x: clampUnit(route.destination.x),
              y: clampUnit(route.destination.y),
            },
          };
        })
        .filter((route): route is MonitorRouteItem & { source: { x: number; y: number } } => Boolean(route)),
    [overlayById, routes],
  );
  const activeRouteCount = Math.min(availableRoutes.length, Math.max(0, visibleCount));
  const activeRoutes = useMemo(() => availableRoutes.slice(0, activeRouteCount), [activeRouteCount, availableRoutes]);
  const [activeRouteIndex, setActiveRouteIndex] = useState(0);
  const [completedRouteCount, setCompletedRouteCount] = useState(0);

  useEffect(() => {
    setActiveRouteIndex(0);
    setCompletedRouteCount(0);
    if (!activeRoutes.length) {
      return;
    }
    const stepMs = 1200;
    let index = 0;
    const timer = window.setInterval(() => {
      index += 1;
      setCompletedRouteCount(Math.min(index, activeRoutes.length));
      if (index >= activeRoutes.length) {
        window.clearInterval(timer);
        setActiveRouteIndex(activeRoutes.length - 1);
        return;
      }
      setActiveRouteIndex(index);
    }, stepMs);
    return () => window.clearInterval(timer);
  }, [activeRoutes.length]);

  const activeRoute = activeRoutes[activeRouteIndex];
  const completedRoutes = activeRoutes.slice(0, completedRouteCount);

  return (
    <div className="monitor-overlay-layer">
      <svg className="monitor-route-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
        {activeRoute ? (
          <path
            key={activeRoute.id}
            d={monitorRouteToSvgPath(activeRoute.source, activeRoute.destination, activeRoute.points)}
            className={`monitor-route target-${activeRoute.target}`}
          />
        ) : null}
      </svg>

      {activeRoute ? (
        <div
          key={`${activeRoute.id}-ghost`}
          className={`monitor-ghost target-${activeRoute.target}`}
          style={
            {
              "--sx": `${activeRoute.source.x * 100}%`,
              "--sy": `${activeRoute.source.y * 100}%`,
              "--dx": `${activeRoute.destination.x * 100}%`,
              "--dy": `${activeRoute.destination.y * 100}%`,
            } as CSSProperties
          }
          title={activeRoute.label}
        />
      ) : null}

      {activeRoute ? (
        <div
          key={`${activeRoute.id}-label`}
          className={`monitor-food-label target-${activeRoute.target}`}
          style={{
            left: `${clampPercent(activeRoute.source.x * 100)}%`,
            top: `${clampPercent(activeRoute.source.y * 100, 12, 90)}%`,
          }}
        >
          {activeRoute.label}
        </div>
      ) : null}

      {completedRoutes.map((route) => (
        <div
          key={`${route.id}-pulse`}
          className={`monitor-endpoint-pulse target-${route.target}`}
          style={{
            left: `${clampPercent(route.destination.x * 100)}%`,
            top: `${clampPercent(route.destination.y * 100, 12, 90)}%`,
          }}
        />
      ))}
    </div>
  );
}

export function DemoOverlayRenderer({ overlays, paths, scenarioId, variant = "default", monitorRoutes = [] }: DemoOverlayRendererProps) {
  const [visibleCount, setVisibleCount] = useState(0);
  const [lockPhase, setLockPhase] = useState<"acquiring" | "locked">("acquiring");
  const isMonitor = scenarioId === "sustainability";
  const isWayfindingLocked = scenarioId === "wayfinding" && variant === "locked";

  useEffect(() => {
    const revealStepMs = isMonitor ? 200 : 240;
    const lockDelayMs = isMonitor ? 950 : 1400;
    setLockPhase("acquiring");
    setVisibleCount(0);
    let current = 0;
    const stepper = window.setInterval(() => {
      current += 1;
      setVisibleCount(current);
      if (current >= overlays.length) {
        window.clearInterval(stepper);
      }
    }, revealStepMs);
    const lockTimer = window.setTimeout(() => setLockPhase("locked"), lockDelayMs);
    return () => {
      window.clearInterval(stepper);
      window.clearTimeout(lockTimer);
    };
  }, [isMonitor, overlays]);

  if (isWayfindingLocked) {
    return <WayfindingARLayer overlays={overlays} paths={paths} />;
  }

  return (
    <div className={`overlay-layer mode-${scenarioId} ${isMonitor ? "monitor-clean" : ""}`}>
      {paths?.map((path, index) => (
        <RoutePath key={path.id} path={path} index={index} />
      ))}

      {isMonitor ? (
        <MonitorOverlayLayer
          visibleCount={visibleCount}
          routes={monitorRoutes}
          overlays={overlays}
        />
      ) : null}

      {!isMonitor
        ? overlays.map((overlay, index) => {
        const isVisible = index < visibleCount;
        return (
          <div
            key={overlay.id}
            className={`overlay-box ${severityClassMap[overlay.severity]} ${isVisible ? "visible" : ""} ${lockPhase}`}
            style={{
              left: `${overlay.x * 100}%`,
              top: `${overlay.y * 100}%`,
              width: `${overlay.width * 100}%`,
              height: `${overlay.height * 100}%`,
              animationDelay: `${index * 220}ms`,
            }}
          >
            <div className="corner tl" />
            <div className="corner tr" />
            <div className="corner bl" />
            <div className="corner br" />
            <div className="overlay-label">
              <span className="overlay-title">{overlay.label}</span>
              <span className="overlay-meta">
                {lockPhase === "acquiring" ? "Acquiring anchor..." : `${overlay.confidence}% • ${overlay.severity}`}
              </span>
            </div>
            <div className="overlay-tether" />
            <span className="overlay-anchor-dot" />
            {overlay.chip ? <span className="overlay-chip">{overlay.chip}</span> : null}
          </div>
        );
        })
        : null}
    </div>
  );
}

