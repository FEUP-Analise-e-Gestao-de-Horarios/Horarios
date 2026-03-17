import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Pages already migrated to React.
// When you migrate a new page, ADD it here.
const REACT_ROUTES = ["/login", "/react-forgot-password"];

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
      // Catch-all: proxy everything to Django by default
      "^/(?!@|node_modules|src).*": {
        target: `http://${backendHost}:8000`,
        changeOrigin: true,
        bypass(req) {
          const url = req.url ?? "";
          // If the URL belongs to a migrated React route,
          // tell Vite to serve index.html instead of proxying
          if (REACT_ROUTES.some((route) => url.startsWith(route))) {
            return "/index.html";
          }
          // Otherwise fall through — proxy to Django
        },
      },
    },
  },
}));
