import { CSSProperties } from 'react';

export type ServerStatus = 'connected' | 'disconnected' | 'reconnecting';

export interface StatusBarProps {
  serverStatus: ServerStatus;
  modelWarm: boolean;
  currentPhase: number;
}

const STATUS_CONFIG: Record<ServerStatus, { color: string; label: string }> = {
  connected: { color: '#22c55e', label: 'Connected' },
  disconnected: { color: '#ef4444', label: 'Disconnected' },
  reconnecting: { color: '#eab308', label: 'Reconnecting…' },
};

export function StatusBar({ serverStatus, modelWarm, currentPhase }: StatusBarProps) {
  const { color, label } = STATUS_CONFIG[serverStatus];

  const barStyle: CSSProperties = {
    position: 'fixed',
    bottom: 0,
    left: 0,
    right: 0,
    height: 32,
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 12px',
    fontFamily: 'monospace',
    fontSize: 12,
    color: '#d1d5db',
    zIndex: 1000,
    backdropFilter: 'blur(8px)',
    borderTop: '1px solid rgba(255, 255, 255, 0.1)',
  };

  const dotStyle: CSSProperties = {
    width: 8,
    height: 8,
    borderRadius: '50%',
    backgroundColor: color,
    boxShadow: `0 0 6px ${color}`,
    animation: serverStatus === 'reconnecting' ? 'pulse 1.5s ease-in-out infinite' : undefined,
  };

  const sectionStyle: CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  };

  return (
    <>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
      <div style={barStyle} role="status" aria-label="Application status bar">
        <div style={sectionStyle}>
          <span style={dotStyle} data-testid="status-dot" />
          <span data-testid="status-label">{label}</span>
        </div>
        <div style={sectionStyle}>
          <span data-testid="model-status">
            Model: {modelWarm ? '🟢 Warm' : '⏳ Cold'}
          </span>
        </div>
        <div style={sectionStyle}>
          <span data-testid="phase-label">Phase {currentPhase}</span>
        </div>
      </div>
    </>
  );
}
