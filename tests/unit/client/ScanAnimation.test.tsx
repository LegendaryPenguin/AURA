import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ScanAnimation } from '../../../client/src/components/ui/ScanAnimation';

describe('ScanAnimation', () => {
  it('renders scan animation when isScanning is true', () => {
    render(<ScanAnimation isScanning={true} />);
    expect(screen.getByTestId('scan-animation')).toBeInTheDocument();
  });

  it('does not render when isScanning is false', () => {
    render(<ScanAnimation isScanning={false} />);
    expect(screen.queryByTestId('scan-animation')).not.toBeInTheDocument();
  });

  it('has progressbar role for accessibility', () => {
    render(<ScanAnimation isScanning={true} />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });
});
