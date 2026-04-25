import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StatusBar } from '../../../client/src/components/ui/StatusBar';

describe('StatusBar', () => {
  it('shows Connected status', () => {
    render(<StatusBar serverStatus="connected" modelWarm={true} currentPhase={2} />);
    expect(screen.getByTestId('status-label')).toHaveTextContent('Connected');
  });

  it('shows Disconnected status', () => {
    render(<StatusBar serverStatus="disconnected" modelWarm={false} currentPhase={0} />);
    expect(screen.getByTestId('status-label')).toHaveTextContent('Disconnected');
  });

  it('shows Reconnecting status', () => {
    render(<StatusBar serverStatus="reconnecting" modelWarm={false} currentPhase={1} />);
    expect(screen.getByTestId('status-label')).toHaveTextContent('Reconnecting');
  });

  it('shows model warm state', () => {
    render(<StatusBar serverStatus="connected" modelWarm={true} currentPhase={2} />);
    expect(screen.getByTestId('model-status')).toHaveTextContent('Warm');
  });

  it('shows model cold state', () => {
    render(<StatusBar serverStatus="connected" modelWarm={false} currentPhase={2} />);
    expect(screen.getByTestId('model-status')).toHaveTextContent('Cold');
  });

  it('shows current phase number', () => {
    render(<StatusBar serverStatus="connected" modelWarm={true} currentPhase={3} />);
    expect(screen.getByTestId('phase-label')).toHaveTextContent('Phase 3');
  });

  it('renders status dot with correct color for connected', () => {
    render(<StatusBar serverStatus="connected" modelWarm={true} currentPhase={0} />);
    const dot = screen.getByTestId('status-dot');
    expect(dot.style.backgroundColor).toBe('rgb(34, 197, 94)');
  });

  it('renders status dot with correct color for disconnected', () => {
    render(<StatusBar serverStatus="disconnected" modelWarm={false} currentPhase={0} />);
    const dot = screen.getByTestId('status-dot');
    expect(dot.style.backgroundColor).toBe('rgb(239, 68, 68)');
  });
});
