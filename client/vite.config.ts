import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API_TARGET = process.env.VITE_API_TARGET ?? "http://localhost:8080";
const isHttps = API_TARGET.startsWith("https");
const wsTarget = API_TARGET.replace(/^https/, "wss").replace(/^http/, "ws");

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/analyze": {
        target: API_TARGET,
        changeOrigin: true,
        secure: false,
      },
      "/health": {
        target: API_TARGET,
        changeOrigin: true,
        secure: false,
      },
      "/api": {
        target: API_TARGET,
        changeOrigin: true,
        secure: false,
      },
      "/ws": {
        target: wsTarget,
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
