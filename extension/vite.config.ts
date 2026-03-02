import { defineConfig } from "vite"
import preact from "@preact/preset-vite"
import { crx } from "@crxjs/vite-plugin"
import manifest from "./manifest.json"
import { resolve } from "path"

export default defineConfig({
  plugins: [
    preact(),
    crx({ manifest }),
  ],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  build: {
    outDir: "dist",
    rollupOptions: {
      input: {
        options: resolve(__dirname, "src/options/index.html"),
        welcome: resolve(__dirname, "src/onboarding/welcome.html"),
      },
    },
  },
})
