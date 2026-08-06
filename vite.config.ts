// @lovable.dev/vite-tanstack-config already includes React, TanStack, Tailwind,
// aliases and the server build. This only adds the local FastAPI proxy.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

export default defineConfig({
  tanstackStart: {
    server: { entry: "server" },
  },
  vite: {
    server: {
      host: "127.0.0.1",
      // A URL pública do ngrok preserva o Host original; o túnel é solicitado
      // explicitamente para esta demonstração local, por isso aceitamos esse host.
      allowedHosts: true,
      proxy: {
        "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
        "/ws": { target: "ws://127.0.0.1:8000", ws: true },
      },
    },
  },
});
