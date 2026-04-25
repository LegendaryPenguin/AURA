import type { CSSProperties } from "react";
import type { OverlayStateItem } from "../../hooks/useOverlay";

interface DiagnosticCardProps {
  overlay: OverlayStateItem;
  onAction?: (overlay: OverlayStateItem) => void;
}

const cardBase: CSSProperties = {
  position: "absolute",
  borderRadius: 12,
  border: "1px solid rgba(59, 130, 246, 0.8)",
  background: "rgba(15, 23, 42, 0.58)",
  backdropFilter: "blur(8px)",
  boxShadow: "0 0 24px rgba(59, 130, 246, 0.48)",
  color: "#dbeafe",
  padding: "0.6rem 0.75rem",
  display: "grid",
  gap: "0.45rem",
  pointerEvents: "auto",
  transition: "opacity 220ms ease, transform 220ms ease",
};

export default function DiagnosticCard({ overlay, onAction }: DiagnosticCardProps) {
  const x1 = overlay.bbox.x;
  const y1 = overlay.bbox.y;
  const width = overlay.bbox.width;
  const stateStyle =
    overlay.animationState === "exiting"
      ? { opacity: 0, transform: "translateY(10px) scale(0.98)" }
      : overlay.animationState === "entering"
        ? { opacity: 0, transform: "translateY(6px) scale(0.99)" }
        : { opacity: 1, transform: "translateY(0) scale(1)" };

  return (
    <article
      role="status"
      aria-live="polite"
      style={{
        ...cardBase,
        left: `${x1 * 100}%`,
        top: `${Math.max(0, y1 * 100 - 12)}%`,
        width: `${Math.max(18, width * 100)}%`,
        ...stateStyle,
      }}
    >
      <header style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem" }}>
        <strong style={{ fontSize: "0.85rem", letterSpacing: "0.01em" }}>Diagnostic Signal</strong>
        <span style={{ fontSize: "0.75rem", color: "#93c5fd" }}>
          {(overlay.confidence * 100).toFixed(0)}%
        </span>
      </header>
      <p style={{ margin: 0, fontSize: "0.82rem", lineHeight: 1.35 }}>{overlay.label}</p>
      <button
        type="button"
        onClick={() => onAction?.(overlay)}
        style={{
          justifySelf: "start",
          fontSize: "0.78rem",
          borderRadius: 8,
          border: "1px solid #60a5fa",
          background: "rgba(30, 64, 175, 0.7)",
          color: "#eff6ff",
          padding: "0.35rem 0.6rem",
          cursor: "pointer",
        }}
      >
        {overlay.action_required ? "Run recommended action" : "Inspect details"}
      </button>
    </article>
  );
}
