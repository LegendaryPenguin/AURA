import type { CSSProperties } from "react";
import type { OverlayStateItem } from "../../hooks/useOverlay";

interface InfoBoxProps {
  overlay: OverlayStateItem;
}

const boxStyle: CSSProperties = {
  position: "absolute",
  borderRadius: 10,
  border: "1px solid rgba(148, 163, 184, 0.8)",
  background: "rgba(17, 24, 39, 0.58)",
  boxShadow: "0 0 18px rgba(148, 163, 184, 0.34)",
  color: "#e2e8f0",
  padding: "0.5rem 0.65rem",
  minWidth: "10rem",
  pointerEvents: "none",
  transition: "opacity 220ms ease, transform 220ms ease",
};

export default function InfoBox({ overlay }: InfoBoxProps) {
  const x1 = overlay.bbox.x;
  const y1 = overlay.bbox.y;
  const stateStyle =
    overlay.animationState === "exiting"
      ? { opacity: 0, transform: "translateY(8px)" }
      : overlay.animationState === "entering"
        ? { opacity: 0, transform: "translateY(4px)" }
        : { opacity: 1, transform: "translateY(0)" };

  return (
    <aside
      role="note"
      style={{
        ...boxStyle,
        left: `${x1 * 100}%`,
        top: `${Math.max(0, y1 * 100 - 8)}%`,
        ...stateStyle,
      }}
    >
      <div style={{ fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "#cbd5e1" }}>
        Info
      </div>
      <p style={{ margin: "0.2rem 0 0", fontSize: "0.82rem", lineHeight: 1.3 }}>{overlay.label}</p>
    </aside>
  );
}
