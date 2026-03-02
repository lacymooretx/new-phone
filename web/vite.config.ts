/// <reference types="vitest/config" />
import path from "path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      events: "events",
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom", "react-router"],
          "vendor-tanstack": ["@tanstack/react-query", "@tanstack/react-table"],
          "vendor-ui": ["lucide-react", "next-themes", "sonner"],
          "vendor-headsets": ["softphone-vendor-headsets"],
          "vendor-charts": ["recharts"],
          "vendor-sip": ["sip.js"],
          "vendor-i18n": ["i18next", "react-i18next", "i18next-browser-languagedetector"],
          "vendor-forms": ["zod", "react-hook-form", "@hookform/resolvers"],
        },
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    exclude: ["e2e/**", "node_modules/**"],
  },
})
