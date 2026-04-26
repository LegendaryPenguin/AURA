import '@testing-library/jest-dom/vitest';

if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class ResizeObserver {
    private cb: ResizeObserverCallback;
    constructor(cb: ResizeObserverCallback) { this.cb = cb; }
    observe() { /* noop in tests */ }
    unobserve() { /* noop in tests */ }
    disconnect() { /* noop in tests */ }
  };
}
