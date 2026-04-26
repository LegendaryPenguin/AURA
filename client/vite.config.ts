import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // Default to HTTP for reliable local dev.
    // Mobile camera over LAN may still require HTTPS (documented in docs/DEMO_PHONE.md).
    https: false,
    // Allow Cloudflare Quick Tunnel hostnames for phone demos.
    allowedHosts: [".trycloudflare.com"],
    proxy: {
      "/api": {
        target: "https://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/ws": {
        target: "wss://localhost:8000",
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
