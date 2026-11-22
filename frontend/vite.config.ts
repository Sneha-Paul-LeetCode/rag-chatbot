import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, requests to /api are forwarded to the Python API on port 8000
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
