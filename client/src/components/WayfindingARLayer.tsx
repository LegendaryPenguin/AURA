import { useMemo, type CSSProperties } from "react";
import type { OverlayBox, OverlayPath } from "../data/demoScenarios";

interface WayfindingARLayerProps {
  overlays: OverlayBox[];
  paths?: OverlayPath[];
}

export function WayfindingARLayer({ overlays, paths }: WayfindingARLayerProps) {
  const chevronLeftOffset = -0.03;
  const destination = overlays.find((overlay) => overlay.id === "exit-door");
  const hazard = overlays.find((overlay) => overlay.id === "chair-obstacle");
  const route = paths?.[0];

  const distanceText = useMemo(() => {
    if (!route || route.points.length < 2) {
      return "~3 m";
    }
    let length = 0;
    for (let i = 1; i < route.points.length; i += 1) {
      const dx = route.points[i].x - route.points[i - 1].x;
      const dy = route.points[i].y - route.points[i - 1].y;
      length += Math.sqrt(dx * dx + dy * dy);
    }
    // Map normalized path length to meters using a rough hallway scale (full
    // frame ~= 5m) so the HUD reads as a believable AR navigation cue.
    const meters = Math.max(1, Math.round(length * 5));
    return `~${meters} m`;
  }, [route]);

  const chevrons = useMemo(() => {
    if (!route) {
      return [];
    }
    const points = route.points;
    const n = points.length;
    if (n < 2) {
      return [];
    }
    return points.slice(0, -1).map((point, i) => {
      // t = 0 at the user's feet (first point), t = 1 at the destination.
      const t = i / (n - 1);
      const scale = 0.55 + 0.9 * (1 - t);
      const baseOpacity = 0.4 + 0.55 * (1 - t * 0.6);
      return {
        id: `chev-${i}`,
        x: Math.max(0.05, Math.min(0.95, point.x + chevronLeftOffset)),
        y: point.y,
        scale,
        baseOpacity,
        enterDelayMs: 200 + i * 90,
        marchDelayMs: 700 + i * 320,
      };
    });
  }, [route, chevronLeftOffset]);

  return (
    <div className="way-ar-layer">
      <div className="way-hud" aria-live="polite">
        <span className="way-hud-arrow" aria-hidden="true" />
        <span className="way-hud-text">Continue straight · {distanceText}</span>
      </div>

      <div className="way-chevron-trail" aria-hidden="true">
        {chevrons.map((chev) => (
          <span
            key={chev.id}
            className="way-chevron"
            style={
              {
                left: `${chev.x * 100}%`,
                top: `${chev.y * 100}%`,
                "--chev-scale": chev.scale,
                "--chev-base": chev.baseOpacity,
              } as CSSProperties
            }
          >
            <span
              className="way-chevron-anim"
              style={{
                animation: `chevronEnter 380ms ease forwards ${chev.enterDelayMs}ms, chevronMarch 1.6s ease-in-out infinite ${chev.marchDelayMs}ms`,
              }}
            >
              <svg viewBox="0 0 40 24" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
                <path
                  d="M 4 20 L 20 6 L 36 20"
                  stroke="#7adcff"
                  strokeWidth="4.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="none"
                />
              </svg>
            </span>
          </span>
        ))}
      </div>
      <div className="way-distance-track" aria-live="polite">
        <span className="way-distance-dot" aria-hidden="true" />
        <span className="way-distance-text">{distanceText} to destination</span>
      </div>

      {destination ? (
        <div
          className="way-pin"
          style={{
            left: `${(destination.x + destination.width / 2) * 100}%`,
            top: `${(destination.y + destination.height * 0.65) * 100}%`,
          }}
        >
          <div className="way-pin-anim">
            <svg viewBox="0 0 24 36" aria-hidden="true">
              <path d="M 12 35 L 12 19" stroke="#062a1c" strokeWidth="2" strokeLinecap="round" />
              <circle cx="12" cy="11" r="9" fill="#5ffba7" stroke="#062a1c" strokeWidth="1.6" />
              <path
                d="M 8 11 L 11 14.5 L 16.5 7.5"
                stroke="#062a1c"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
              />
            </svg>
          </div>
        </div>
      ) : null}

      {hazard ? (
        <div
          className="way-cone"
          style={{
            left: `${(hazard.x + hazard.width / 2) * 100}%`,
            top: `${(hazard.y + hazard.height / 2) * 100}%`,
          }}
        >
          <div className="way-cone-anim">
            <svg viewBox="0 0 32 32" aria-hidden="true">
              <path
                d="M 16 4 L 29 28 L 3 28 Z"
                fill="rgba(255, 138, 78, 0.92)"
                stroke="#ffe2cf"
                strokeWidth="1.6"
                strokeLinejoin="round"
              />
              <rect x="14.5" y="11" width="3" height="8" rx="1.4" fill="#1a0805" />
              <rect x="14.5" y="21" width="3" height="3" rx="1.4" fill="#1a0805" />
            </svg>
            <span className="way-cone-text">Avoid right side</span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
