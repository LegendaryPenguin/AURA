import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Dev server defaults:
 * - HTTP on localhost (avoids Windows Chrome ERR_SSL_VERSION_OR_CIPHER_MISMATCH with Vite's dev cert).
 * - Opt-in HTTPS: `VITE_DEV_HTTPS=true npm run dev`
 * - LAN / phone: `npm run dev -- --host` (or set `server.host` via Vite CLI / env in your shell).
 */
const useDevHttps = process.env.VITE_DEV_HTTPS === "true";

export default defineConfig({
  plugins: [react()],
  server: {
    https: useDevHttps,
    allowedHosts: true,
    proxy: {
      "/api": {
        target: "http://localhost:8443",
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/ws": {
        target: "ws://localhost:8443",
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
