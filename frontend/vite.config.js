import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Requests to /api/* are forwarded to the FastAPI backend, so no CORS setup is needed.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://localhost:8000" },
  },
});
