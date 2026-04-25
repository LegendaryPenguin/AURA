import { useEffect, CSSProperties } from 'react';

export type AgentActionType = 'triggered' | 'resolved';

export interface AgentActionToastProps {
  message: string;
  type: AgentActionType;
  visible: boolean;
  onDismiss?: () => void;
  autoDismissMs?: number;
}

const TOAST_COLORS: Record<AgentActionType, { bg: string; border: string; icon: string }> = {
  triggered: {
    bg: 'rgba(180, 130, 20, 0.9)',
    border: 'rgba(234, 179, 8, 0.6)',
    icon: '⚡',
  },
  resolved: {
    bg: 'rgba(20, 130, 70, 0.9)',
    border: 'rgba(34, 197, 94, 0.6)',
    icon: '✓',
  },
};

export function AgentActionToast({
  message,
  type,
  visible,
  onDismiss,
  autoDismissMs = 4000,
}: AgentActionToastProps) {
  useEffect(() => {
    if (!visible || !onDismiss) return;

    const timer = setTimeout(onDismiss, autoDismissMs);
    return () => clearTimeout(timer);
  }, [visible, onDismiss, autoDismissMs]);

  if (!visible) return null;

  const { bg, border, icon } = TOAST_COLORS[type];

  const toastStyle: CSSProperties = {
    position: 'fixed',
    top: 16,
    right: 16,
    padding: '10px 16px',
    backgroundColor: bg,
    border: `1px solid ${border}`,
    borderRadius: 8,
    color: '#fff',
    fontFamily: 'system-ui, sans-serif',
    fontSize: 14,
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    zIndex: 2000,
    backdropFilter: 'blur(8px)',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
    animation: 'toastSlideIn 0.3s ease-out',
    maxWidth: 320,
  };

  return (
    <>
      <style>{`
        @keyframes toastSlideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>
      <div style={toastStyle} role="alert" data-testid="agent-toast">
        <span>{icon}</span>
        <span>
          <strong style={{ textTransform: 'capitalize' }}>{type}</strong>
          {' — '}
          {message}
        </span>
      </div>
    </>
  );
}
