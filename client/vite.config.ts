import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    https: true,
    proxy: {
      "/analyze": {
        target: "https://localhost:8443",
        changeOrigin: true,
        secure: false,
      },
      "/health": {
        target: "https://localhost:8443",
        changeOrigin: true,
        secure: false,
      },
      "/api": {
        target: "https://localhost:8443",
        changeOrigin: true,
        secure: false,
      },
      "/ws": {
        target: "wss://localhost:8443",
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
