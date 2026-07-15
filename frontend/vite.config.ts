import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  // API base: in dev, proxy /api to the local backend. In prod, set VITE_API_BASE.
  // Use 127.0.0.1 (not localhost) to avoid IPv6/IPv4 mismatch in the Node proxy.
  proxy: {
    "/api": "http://127.0.0.1:8000",
  },
});
