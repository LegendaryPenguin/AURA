import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Dev server defaults:
 * - HTTP on localhost (avoids Windows Chrome ERR_SSL_VERSION_OR_CIPHER_MISMATCH with Vite's dev cert).
 * - Opt-in HTTPS: `VITE_DEV_HTTPS=true npm run dev`
 * - LAN / phone: `npm run dev -- --host` (or set `server.host` via Vite CLI / env in your shell).
 */
const useDevHttps = process.env.VITE_DEV_HTTPS === "true";
const realApiTarget = process.env.VITE_API_TARGET_REAL ?? "http://localhost:9443";
const qwen3bApiTarget = process.env.VITE_API_TARGET_QWEN3B ?? "http://127.0.0.1:9451";
const qwen7bApiTarget = process.env.VITE_API_TARGET_QWEN7B ?? "http://127.0.0.1:9453";
const moondreamApiTarget = process.env.VITE_API_TARGET_MOONDREAM2 ?? "http://127.0.0.1:9460";
const videoSimApiTarget = process.env.VITE_API_TARGET_VIDEO_SIM ?? moondreamApiTarget;

export default defineConfig({
  plugins: [react()],
  server: {
    https: useDevHttps,
    allowedHosts: true,
    proxy: {
      "/api/video-sim": {
        target: videoSimApiTarget,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/api/model/qwen3b": {
        target: qwen3bApiTarget,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api\/model\/qwen3b/, ""),
      },
      "/api/model/qwen7b": {
        target: qwen7bApiTarget,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api\/model\/qwen7b/, ""),
      },
      "/api/model/moondream2": {
        target: moondreamApiTarget,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api\/model\/moondream2/, ""),
      },
      "/api": {
        target: realApiTarget,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/ws": {
        target: "ws://localhost:9443",
        changeOrigin: true,
        secure: false,
        ws: true,
      },
    },
  },
  build: {
    sourcemap: true,
  },
});
