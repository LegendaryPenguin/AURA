import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ConfidenceIndicator } from '../../../client/src/components/ui/ConfidenceIndicator';

describe('ConfidenceIndicator', () => {
  it('renders green dot for high confidence (>0.8)', () => {
    render(<ConfidenceIndicator confidence={0.92} />);
    const dot = screen.getByTestId('confidence-dot');
    expect(dot.style.backgroundColor).toBe('rgb(34, 197, 94)');
  });

  it('renders yellow dot for medium confidence (>0.5, <=0.8)', () => {
    render(<ConfidenceIndicator confidence={0.65} />);
    const dot = screen.getByTestId('confidence-dot');
    expect(dot.style.backgroundColor).toBe('rgb(234, 179, 8)');
  });

  it('renders red dot for low confidence (<=0.5)', () => {
    render(<ConfidenceIndicator confidence={0.3} />);
    const dot = screen.getByTestId('confidence-dot');
    expect(dot.style.backgroundColor).toBe('rgb(239, 68, 68)');
  });

  it('renders at boundary: 0.8 is yellow', () => {
    render(<ConfidenceIndicator confidence={0.8} />);
    const dot = screen.getByTestId('confidence-dot');
    expect(dot.style.backgroundColor).toBe('rgb(234, 179, 8)');
  });

  it('renders at boundary: 0.5 is red', () => {
    render(<ConfidenceIndicator confidence={0.5} />);
    const dot = screen.getByTestId('confidence-dot');
    expect(dot.style.backgroundColor).toBe('rgb(239, 68, 68)');
  });

  it('shows percentage text', () => {
    render(<ConfidenceIndicator confidence={0.92} />);
    expect(screen.getByText('92%')).toBeInTheDocument();
  });

  it('has accessible label', () => {
    render(<ConfidenceIndicator confidence={0.92} />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Confidence: High');
  });
});
