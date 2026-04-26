import { useEffect, useMemo, useState } from "react";
import type { OverlayBox, OverlayPath, OverlaySeverity } from "../data/demoScenarios";

interface DemoOverlayRendererProps {
  overlays: OverlayBox[];
  paths?: OverlayPath[];
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

export function DemoOverlayRenderer({ overlays, paths }: DemoOverlayRendererProps) {
  const [visibleCount, setVisibleCount] = useState(0);

  useEffect(() => {
    setVisibleCount(0);
    let current = 0;
    const stepper = window.setInterval(() => {
      current += 1;
      setVisibleCount(current);
      if (current >= overlays.length) {
        window.clearInterval(stepper);
      }
    }, 240);
    return () => window.clearInterval(stepper);
  }, [overlays]);

  return (
    <div className="overlay-layer">
      {paths?.map((path, index) => (
        <RoutePath key={path.id} path={path} index={index} />
      ))}

      {overlays.map((overlay, index) => {
        const isVisible = index < visibleCount;
        return (
          <div
            key={overlay.id}
            className={`overlay-box ${severityClassMap[overlay.severity]} ${isVisible ? "visible" : ""}`}
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
                {overlay.confidence}% • {overlay.severity}
              </span>
            </div>
            {overlay.chip ? <span className="overlay-chip">{overlay.chip}</span> : null}
          </div>
        );
      })}
    </div>
  );
}

