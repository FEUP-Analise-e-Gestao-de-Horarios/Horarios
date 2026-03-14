import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Pages already migrated to React.
// When you migrate a new page, ADD it here.
const REACT_ROUTES = ["/react-test", "/react-test-2"];

export default defineConfig({
    plugins: [react()],
    base: "/static/frontend/",
    build: {
        // Output directly into Django's static/frontend/ directory
        outDir: "../backend/src/static/frontend",
        emptyOutDir: true,
    },
    server: {
        proxy: {
            // Catch-all: proxy everything to Django by default
            "^/(?!@vite|@fs|node_modules|src).*": {
                target: "http://localhost:8000",
                changeOrigin: true,
                bypass(req) {
                    const url = req.url ?? "";
                    // If the URL belongs to a migrated React route,
                    // tell Vite to serve index.html instead of proxying
                    if (REACT_ROUTES.some(route => url.startsWith(route))) {
                        return "/index.html";
                    }
                    // Otherwise fall through — proxy to Django
                },
            },
        },
    },
});
