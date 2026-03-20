import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Allow the Docker dev setup to point the proxy at the backend service.
// Set BACKEND_HOST=backend when running via docker-compose.dev.yml.
const backendHost = process.env.BACKEND_HOST ?? "localhost";

export default defineConfig(({ command }) => ({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  // In production Django serves assets under /static/frontend/; in dev Vite
  // serves from root so React Router and asset paths resolve correctly.
  base: command === "build" ? "/static/frontend/" : "/",
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api/": {
        target: `http://${backendHost}:8000`,
        changeOrigin: true,
      },
    },
  },
}));
