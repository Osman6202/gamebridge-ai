import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  // API base: in dev, proxy /api to the local backend. In prod, set VITE_API_BASE.
  proxy: {
    "/api": "http://localhost:8000",
  },
});
