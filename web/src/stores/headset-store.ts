import { create } from "zustand"

interface HeadsetState {
  isSupported: boolean
  isConnected: boolean
  deviceName: string | null
  vendorName: string | null

  setSupported: (supported: boolean) => void
  setConnected: (connected: boolean, deviceName?: string | null, vendorName?: string | null) => void
  reset: () => void
}

export const useHeadsetStore = create<HeadsetState>((set) => ({
  isSupported: typeof navigator !== "undefined" && "hid" in navigator,
  isConnected: false,
  deviceName: null,
  vendorName: null,

  setSupported: (supported) => set({ isSupported: supported }),

  setConnected: (connected, deviceName = null, vendorName = null) =>
    set({ isConnected: connected, deviceName, vendorName }),

  reset: () => set({ isConnected: false, deviceName: null, vendorName: null }),
}))
