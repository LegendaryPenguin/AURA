import type { CSSProperties } from "react";
import type { OverlayStateItem } from "../../hooks/useOverlay";

interface HazardWarningProps {
  overlay: OverlayStateItem;
}

const containerStyle: CSSProperties = {
  position: "absolute",
  borderRadius: 12,
  border: "1px solid rgba(248, 113, 113, 0.92)",
  background: "rgba(69, 10, 10, 0.62)",
  color: "#fee2e2",
  boxShadow: "0 0 26px rgba(239, 68, 68, 0.56)",
  padding: "0.6rem 0.75rem",
  minWidth: "12rem",
  pointerEvents: "none",
  animation: "aura-hazard-pulse 1s ease-in-out infinite",
  transition: "opacity 220ms ease, transform 220ms ease",
};

export default function HazardWarning({ overlay }: HazardWarningProps) {
  const x1 = overlay.bbox.x;
  const y1 = overlay.bbox.y;
  const severity = overlay.severity ?? "high";
  const stateStyle =
    overlay.animationState === "exiting"
      ? { opacity: 0, transform: "scale(0.97)" }
      : overlay.animationState === "entering"
        ? { opacity: 0, transform: "scale(0.99)" }
        : { opacity: 1, transform: "scale(1)" };

  return (
    <>
      <style>{`
        @keyframes aura-hazard-pulse {
          0%, 100% { box-shadow: 0 0 14px rgba(239, 68, 68, 0.35); }
          50% { box-shadow: 0 0 34px rgba(239, 68, 68, 0.75); }
        }
      `}</style>
      <article
        role="alert"
        style={{
          ...containerStyle,
          left: `${x1 * 100}%`,
          top: `${Math.max(0, y1 * 100 - 10)}%`,
          ...stateStyle,
        }}
      >
        <div style={{ fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "#fca5a5" }}>
          Hazard Warning
        </div>
        <div style={{ marginTop: "0.15rem", fontWeight: 600 }}>{overlay.label}</div>
        <div style={{ marginTop: "0.2rem", fontSize: "0.8rem", color: "#fecaca" }}>
          Severity: {severity.toUpperCase()}
        </div>
      </article>
    </>
  );
}
