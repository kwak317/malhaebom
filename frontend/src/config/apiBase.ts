const configuredApiBase = import.meta.env.VITE_API_BASE_URL?.trim().replace(/\/$/, "") || "";

// Production Compose uses the current origin and lets Nginx proxy API paths.
// Vite development keeps the historical local API default for convenience.
export const API_BASE_URL = configuredApiBase || (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");
