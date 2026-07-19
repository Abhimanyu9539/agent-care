import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the browser only talks to Vite, which passes /api on to FastAPI.
// One origin means the session cookie just works, with no CORS.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
