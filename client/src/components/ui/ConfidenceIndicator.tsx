import { CSSProperties } from 'react';

export interface ConfidenceIndicatorProps {
  confidence: number;
  size?: number;
}

function getConfidenceColor(confidence: number): string {
  if (confidence > 0.8) return '#22c55e';
  if (confidence > 0.5) return '#eab308';
  return '#ef4444';
}

function getConfidenceLabel(confidence: number): string {
  if (confidence > 0.8) return 'High';
  if (confidence > 0.5) return 'Medium';
  return 'Low';
}

export function ConfidenceIndicator({ confidence, size = 12 }: ConfidenceIndicatorProps) {
  const color = getConfidenceColor(confidence);
  const label = getConfidenceLabel(confidence);

  const dotStyle: CSSProperties = {
    width: size,
    height: size,
    borderRadius: '50%',
    backgroundColor: color,
    display: 'inline-block',
    boxShadow: `0 0 ${size / 2}px ${color}80`,
  };

  const containerStyle: CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
  };

  return (
    <span style={containerStyle} role="status" aria-label={`Confidence: ${label}`}>
      <span
        data-testid="confidence-dot"
        style={dotStyle}
      />
      <span style={{ fontSize: 12, color: '#d1d5db', fontFamily: 'monospace' }}>
        {(confidence * 100).toFixed(0)}%
      </span>
    </span>
  );
}
