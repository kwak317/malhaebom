import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import type { Connect } from "vite";

const serviceEntryRoutes: Connect.NextHandleFunction = (req, _res, next) => {
  const url = new URL(req.url || "/", "http://localhost");
  if (url.pathname === "/intro" || url.pathname === "/intro/") req.url = "/index.html" + url.search;
  else if (/^\/(app(?:\/|$)|practice(?:\/|$)|design$|demo\/)/.test(url.pathname)) req.url = "/app/index.html" + url.search;
  next();
};

export default defineConfig({
  plugins: [react(), {
    name: "service-entry-routes",
    configureServer(server) { server.middlewares.use(serviceEntryRoutes); },
    configurePreviewServer(server) { server.middlewares.use(serviceEntryRoutes); },
  }],
  build: {
    rollupOptions: { input: { intro: resolve(__dirname, "index.html"), app: resolve(__dirname, "app/index.html") } },
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/analysis-jobs": "http://127.0.0.1:8000",
      "/practice-records": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
  },
});
