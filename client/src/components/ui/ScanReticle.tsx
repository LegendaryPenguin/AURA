import { CSSProperties } from 'react';

export interface ScanReticleProps {
  visible: boolean;
  size?: number;
  color?: string;
}

export function ScanReticle({
  visible,
  size = 200,
  color = 'rgba(0, 200, 255, 0.6)',
}: ScanReticleProps) {
  if (!visible) return null;

  const containerStyle: CSSProperties = {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    width: size,
    height: size,
    pointerEvents: 'none',
    zIndex: 50,
  };

  const cornerLength = size * 0.2;
  const strokeWidth = 2;

  return (
    <div style={containerStyle} data-testid="scan-reticle" aria-hidden="true">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Top-left corner */}
        <path
          d={`M ${strokeWidth} ${cornerLength} L ${strokeWidth} ${strokeWidth} L ${cornerLength} ${strokeWidth}`}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Top-right corner */}
        <path
          d={`M ${size - cornerLength} ${strokeWidth} L ${size - strokeWidth} ${strokeWidth} L ${size - strokeWidth} ${cornerLength}`}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Bottom-left corner */}
        <path
          d={`M ${strokeWidth} ${size - cornerLength} L ${strokeWidth} ${size - strokeWidth} L ${cornerLength} ${size - strokeWidth}`}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Bottom-right corner */}
        <path
          d={`M ${size - cornerLength} ${size - strokeWidth} L ${size - strokeWidth} ${size - strokeWidth} L ${size - strokeWidth} ${size - cornerLength}`}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Center crosshair */}
        <line
          x1={size / 2}
          y1={size / 2 - 10}
          x2={size / 2}
          y2={size / 2 + 10}
          stroke={color}
          strokeWidth={1}
          opacity={0.8}
        />
        <line
          x1={size / 2 - 10}
          y1={size / 2}
          x2={size / 2 + 10}
          y2={size / 2}
          stroke={color}
          strokeWidth={1}
          opacity={0.8}
        />
      </svg>
    </div>
  );
}
