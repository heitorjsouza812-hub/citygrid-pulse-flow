// @lovable.dev/vite-tanstack-config already includes React, TanStack, Tailwind,
// aliases and the server build. This only adds the local FastAPI proxy.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

const publicAppUrl = process.env.CITYGRID_PUBLIC_APP_URL;
const publicHost = publicAppUrl ? new URL(publicAppUrl).hostname : undefined;

export default defineConfig({
  tanstackStart: {
    server: { entry: "server" },
  },
  vite: {
    server: {
      // Deliberate LAN use: CITYGRID_FRONTEND_HOST=0.0.0.0. Do not use an
      // unrestricted allowedHosts override for a published deployment.
      host: process.env.CITYGRID_FRONTEND_HOST ?? process.env.CITYGRID_HOST ?? "127.0.0.1",
      // Accept only the exact configured public host, never an unrestricted wildcard.
      ...(publicHost ? { allowedHosts: [publicHost] } : {}),
      proxy: {
        "/api": {
          target: process.env.CITYGRID_API_INTERNAL_URL ?? "http://127.0.0.1:8000",
          changeOrigin: true,
        },
        "/ws": { target: process.env.CITYGRID_WS_INTERNAL_URL ?? "ws://127.0.0.1:8000", ws: true },
      },
    },
  },
});
