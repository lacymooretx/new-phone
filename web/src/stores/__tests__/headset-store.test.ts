import { describe, it, expect, beforeEach } from "vitest"
import { useHeadsetStore } from "../headset-store"

describe("headset-store", () => {
  beforeEach(() => {
    useHeadsetStore.getState().reset()
  })

  // ── Initial state ──────────────────────────────────────────────────
  describe("initial state", () => {
    it("defaults isConnected to false", () => {
      expect(useHeadsetStore.getState().isConnected).toBe(false)
    })

    it("defaults deviceName to null", () => {
      expect(useHeadsetStore.getState().deviceName).toBeNull()
    })

    it("defaults vendorName to null", () => {
      expect(useHeadsetStore.getState().vendorName).toBeNull()
    })
  })

  // ── setSupported ───────────────────────────────────────────────────
  describe("setSupported()", () => {
    it("sets isSupported to true", () => {
      useHeadsetStore.getState().setSupported(true)
      expect(useHeadsetStore.getState().isSupported).toBe(true)
    })

    it("sets isSupported to false", () => {
      useHeadsetStore.getState().setSupported(false)
      expect(useHeadsetStore.getState().isSupported).toBe(false)
    })
  })

  // ── setConnected ───────────────────────────────────────────────────
  describe("setConnected()", () => {
    it("sets connected with device and vendor name", () => {
      useHeadsetStore.getState().setConnected(true, "Jabra Evolve2 75", "Jabra")

      const state = useHeadsetStore.getState()
      expect(state.isConnected).toBe(true)
      expect(state.deviceName).toBe("Jabra Evolve2 75")
      expect(state.vendorName).toBe("Jabra")
    })

    it("sets disconnected and clears names when only connected=false", () => {
      // Connect first
      useHeadsetStore.getState().setConnected(true, "Poly Voyager", "Poly")
      expect(useHeadsetStore.getState().isConnected).toBe(true)

      // Disconnect
      useHeadsetStore.getState().setConnected(false)

      const state = useHeadsetStore.getState()
      expect(state.isConnected).toBe(false)
      expect(state.deviceName).toBeNull()
      expect(state.vendorName).toBeNull()
    })

    it("defaults deviceName and vendorName to null when not provided", () => {
      useHeadsetStore.getState().setConnected(true)

      const state = useHeadsetStore.getState()
      expect(state.isConnected).toBe(true)
      expect(state.deviceName).toBeNull()
      expect(state.vendorName).toBeNull()
    })
  })

  // ── reset ──────────────────────────────────────────────────────────
  describe("reset()", () => {
    it("resets connection state but preserves isSupported", () => {
      useHeadsetStore.getState().setSupported(true)
      useHeadsetStore.getState().setConnected(true, "Headset X", "Vendor Y")

      useHeadsetStore.getState().reset()

      const state = useHeadsetStore.getState()
      expect(state.isConnected).toBe(false)
      expect(state.deviceName).toBeNull()
      expect(state.vendorName).toBeNull()
      // isSupported is NOT reset by reset()
      expect(state.isSupported).toBe(true)
    })
  })
})
