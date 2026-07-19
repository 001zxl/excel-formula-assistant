import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    https: true,
    headers: {
      "Access-Control-Allow-Origin": "*",
    },
    proxy: {
      "/api": {
        target: "https://localhost:8100",
        secure: false,
        changeOrigin: true,
      },
      "/health": {
        target: "https://localhost:8100",
        secure: false,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
  },
});
