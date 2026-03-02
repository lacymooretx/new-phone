import "@testing-library/jest-dom/vitest"
import { cleanup } from "@testing-library/react"
import { afterEach, beforeAll, afterAll } from "vitest"
import { server } from "./handlers"

// Node 22+ exposes a built-in `localStorage` that lacks the standard Web
// Storage API methods (getItem, setItem, etc.).  When vitest uses jsdom the
// jsdom `localStorage` should take over, but the Node built-in can shadow it.
// Provide a spec-compliant in-memory implementation so every test has a
// predictable `localStorage`.
if (
  typeof globalThis.localStorage === "undefined" ||
  typeof globalThis.localStorage.getItem !== "function"
) {
  const store: Record<string, string> = {}
  const storage: Storage = {
    getItem: (key: string) => (key in store ? store[key] : null),
    setItem: (key: string, value: string) => {
      store[key] = String(value)
    },
    removeItem: (key: string) => {
      delete store[key]
    },
    clear: () => {
      for (const k of Object.keys(store)) delete store[k]
    },
    get length() {
      return Object.keys(store).length
    },
    key: (index: number) => Object.keys(store)[index] ?? null,
  }
  Object.defineProperty(globalThis, "localStorage", {
    value: storage,
    writable: true,
    configurable: true,
  })
}

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }))
afterEach(() => {
  cleanup()
  server.resetHandlers()
  localStorage.clear()
})
afterAll(() => server.close())
