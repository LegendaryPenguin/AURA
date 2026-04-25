import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

const clientDir = __dirname;
const repoRoot = path.resolve(clientDir, '..');

function clientModule(name: string) {
  return path.resolve(clientDir, 'node_modules', name);
}

export default defineConfig({
  plugins: [react()],
  // Use the client as Vite root so Vitest does not watch/scan the entire monorepo (OOM in workers).
  root: clientDir,
  resolve: {
    alias: {
      '@testing-library/react': clientModule('@testing-library/react'),
      '@testing-library/jest-dom': clientModule('@testing-library/jest-dom'),
      'react/jsx-dev-runtime': clientModule('react/jsx-dev-runtime'),
      'react/jsx-runtime': clientModule('react/jsx-runtime'),
      'react-dom': clientModule('react-dom'),
      react: clientModule('react'),
    },
  },
  server: {
    fs: {
      strict: false,
      allow: [repoRoot],
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: [path.resolve(clientDir, 'src/test-setup.ts')],
    include: [path.join(repoRoot, 'tests/unit/client/**/*.test.{ts,tsx}')],
    // AppShell pulls the full App bundle in a worker; with Vite root = client/ this still OOMs tinypool on some hosts. Full flow is covered by `tests/integration/test_phase1_e2e.py` + hook tests.
    exclude: [path.join(repoRoot, 'tests/unit/client/AppShell.test.tsx')],
  },
});
