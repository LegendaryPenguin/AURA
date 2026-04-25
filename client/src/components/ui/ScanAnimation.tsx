import { CSSProperties } from 'react';

export interface ScanAnimationProps {
  isScanning: boolean;
}

export function ScanAnimation({ isScanning }: ScanAnimationProps) {
  if (!isScanning) return null;

  const containerStyle: CSSProperties = {
    position: 'absolute',
    inset: 0,
    overflow: 'hidden',
    pointerEvents: 'none',
    zIndex: 40,
  };

  const lineStyle: CSSProperties = {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 2,
    background: 'linear-gradient(90deg, transparent, rgba(0, 200, 255, 0.8), transparent)',
    boxShadow: '0 0 12px rgba(0, 200, 255, 0.5), 0 0 24px rgba(0, 200, 255, 0.2)',
    animation: 'scanSweep 2s ease-in-out infinite',
  };

  return (
    <>
      <style>{`
        @keyframes scanSweep {
          0% { top: 0%; opacity: 0; }
          10% { opacity: 1; }
          90% { opacity: 1; }
          100% { top: 100%; opacity: 0; }
        }
      `}</style>
      <div style={containerStyle} data-testid="scan-animation" role="progressbar" aria-label="Scanning">
        <div style={lineStyle} />
      </div>
    </>
  );
}
