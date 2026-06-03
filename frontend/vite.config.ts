import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // Dev-only port. The backend owns :8000, so the Vite dev server runs on its
    // own port (8001) and proxies API calls to the backend. In Docker there is no
    // Vite: the nginx-served frontend and the backend are unified behind :8000.
    port: 8001,
    proxy: {
      "/chat": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: [],
  },
});
