import { describe, it, expect, beforeEach, vi } from "vitest"
import { useSoftphoneStore, type CallState } from "../softphone-store"

const mockSipClientInstance = {
  connect: vi.fn().mockResolvedValue(undefined),
  disconnect: vi.fn().mockResolvedValue(undefined),
  setRemoteAudio: vi.fn(),
  makeCall: vi.fn().mockResolvedValue(undefined),
  answerCall: vi.fn().mockResolvedValue(undefined),
  declineCall: vi.fn().mockResolvedValue(undefined),
  hangup: vi.fn().mockResolvedValue(undefined),
  toggleMute: vi.fn().mockReturnValue(true),
  toggleHold: vi.fn().mockResolvedValue(true),
  sendDTMF: vi.fn(),
  getRemoteIdentity: vi.fn().mockReturnValue("Alice"),
}

// Mock the SipClient class so we can test store logic without real SIP connections
vi.mock("@/lib/sip-client", () => ({
  SipClient: class MockSipClient {
    constructor() {
      Object.assign(this, mockSipClientInstance)
    }
  },
}))

vi.mock("@/lib/desktop-bridge", () => ({
  isDesktop: vi.fn().mockReturnValue(false),
  showNativeNotification: vi.fn(),
}))

const initialState = {
  status: "disconnected" as const,
  callState: "idle" as CallState,
  callDirection: null,
  remoteIdentity: "",
  callStartTime: null,
  isMuted: false,
  isOnHold: false,
  panelOpen: false,
  panelMinimized: false,
}

describe("softphone-store", () => {
  beforeEach(() => {
    useSoftphoneStore.setState(initialState)
    vi.clearAllMocks()
  })

  // ── Initial state ──────────────────────────────────────────────────
  describe("initial state", () => {
    it("has disconnected status", () => {
      expect(useSoftphoneStore.getState().status).toBe("disconnected")
    })

    it("has idle call state", () => {
      expect(useSoftphoneStore.getState().callState).toBe("idle")
    })

    it("has null call direction", () => {
      expect(useSoftphoneStore.getState().callDirection).toBeNull()
    })

    it("has empty remote identity", () => {
      expect(useSoftphoneStore.getState().remoteIdentity).toBe("")
    })

    it("has null call start time", () => {
      expect(useSoftphoneStore.getState().callStartTime).toBeNull()
    })

    it("is not muted", () => {
      expect(useSoftphoneStore.getState().isMuted).toBe(false)
    })

    it("is not on hold", () => {
      expect(useSoftphoneStore.getState().isOnHold).toBe(false)
    })

    it("panel is closed", () => {
      expect(useSoftphoneStore.getState().panelOpen).toBe(false)
    })

    it("panel is not minimized", () => {
      expect(useSoftphoneStore.getState().panelMinimized).toBe(false)
    })
  })

  // ── makeCall ───────────────────────────────────────────────────────
  describe("makeCall()", () => {
    it("sets callState to ringing_out with outbound direction", async () => {
      const fakeAudio = document.createElement("audio")
      await useSoftphoneStore.getState().connect(
        {
          wssUrl: "wss://test",
          sipUsername: "user",
          sipPassword: "pass",
          sipDomain: "test.com",
          displayName: "Test",
        },
        fakeAudio,
      )

      await useSoftphoneStore.getState().makeCall("1001")

      const state = useSoftphoneStore.getState()
      expect(state.callState).toBe("ringing_out")
      expect(state.callDirection).toBe("outbound")
      expect(state.remoteIdentity).toBe("1001")
      expect(state.panelOpen).toBe(true)
      expect(state.panelMinimized).toBe(false)
    })

    it("calls sipClient.makeCall with the target", async () => {
      const fakeAudio = document.createElement("audio")
      await useSoftphoneStore.getState().connect(
        {
          wssUrl: "wss://test",
          sipUsername: "user",
          sipPassword: "pass",
          sipDomain: "test.com",
          displayName: "Test",
        },
        fakeAudio,
      )

      await useSoftphoneStore.getState().makeCall("2002")

      expect(mockSipClientInstance.makeCall).toHaveBeenCalledWith("2002")
    })
  })

  // ── declineCall ────────────────────────────────────────────────────
  describe("declineCall()", () => {
    it("resets call state to idle when sipClient exists", async () => {
      const fakeAudio = document.createElement("audio")
      await useSoftphoneStore.getState().connect(
        {
          wssUrl: "wss://test",
          sipUsername: "user",
          sipPassword: "pass",
          sipDomain: "test.com",
          displayName: "Test",
        },
        fakeAudio,
      )

      useSoftphoneStore.setState({
        callState: "ringing_in",
        callDirection: "inbound",
        remoteIdentity: "2001",
      })

      await useSoftphoneStore.getState().declineCall()

      const state = useSoftphoneStore.getState()
      expect(state.callState).toBe("idle")
      expect(state.callDirection).toBeNull()
      expect(state.remoteIdentity).toBe("")
    })
  })

  // ── hangup ─────────────────────────────────────────────────────────
  describe("hangup()", () => {
    it("resets all call state fields", async () => {
      const fakeAudio = document.createElement("audio")
      await useSoftphoneStore.getState().connect(
        {
          wssUrl: "wss://test",
          sipUsername: "user",
          sipPassword: "pass",
          sipDomain: "test.com",
          displayName: "Test",
        },
        fakeAudio,
      )

      useSoftphoneStore.setState({
        callState: "connected",
        callDirection: "outbound",
        remoteIdentity: "3001",
        callStartTime: Date.now(),
        isMuted: true,
        isOnHold: false,
      })

      await useSoftphoneStore.getState().hangup()

      const state = useSoftphoneStore.getState()
      expect(state.callState).toBe("idle")
      expect(state.callDirection).toBeNull()
      expect(state.remoteIdentity).toBe("")
      expect(state.callStartTime).toBeNull()
      expect(state.isMuted).toBe(false)
      expect(state.isOnHold).toBe(false)
    })
  })

  // ── disconnect ─────────────────────────────────────────────────────
  describe("disconnect()", () => {
    it("resets all state to initial values", async () => {
      useSoftphoneStore.setState({
        status: "registered",
        callState: "connected",
        callDirection: "outbound",
        remoteIdentity: "4001",
        callStartTime: 1234567890,
        isMuted: true,
        isOnHold: true,
      })

      await useSoftphoneStore.getState().disconnect()

      const state = useSoftphoneStore.getState()
      expect(state.status).toBe("disconnected")
      expect(state.callState).toBe("idle")
      expect(state.callDirection).toBeNull()
      expect(state.remoteIdentity).toBe("")
      expect(state.callStartTime).toBeNull()
      expect(state.isMuted).toBe(false)
      expect(state.isOnHold).toBe(false)
    })
  })

  // ── togglePanel ────────────────────────────────────────────────────
  describe("togglePanel()", () => {
    it("opens panel when closed", () => {
      useSoftphoneStore.setState({ panelOpen: false, panelMinimized: false })
      useSoftphoneStore.getState().togglePanel()

      expect(useSoftphoneStore.getState().panelOpen).toBe(true)
      expect(useSoftphoneStore.getState().panelMinimized).toBe(false)
    })

    it("closes panel when open and not minimized", () => {
      useSoftphoneStore.setState({ panelOpen: true, panelMinimized: false })
      useSoftphoneStore.getState().togglePanel()

      expect(useSoftphoneStore.getState().panelOpen).toBe(false)
    })

    it("expands panel when minimized", () => {
      useSoftphoneStore.setState({ panelOpen: true, panelMinimized: true })
      useSoftphoneStore.getState().togglePanel()

      expect(useSoftphoneStore.getState().panelOpen).toBe(true)
      expect(useSoftphoneStore.getState().panelMinimized).toBe(false)
    })
  })

  // ── minimizePanel / expandPanel ────────────────────────────────────
  describe("minimizePanel()", () => {
    it("sets panelMinimized to true", () => {
      useSoftphoneStore.setState({ panelOpen: true, panelMinimized: false })
      useSoftphoneStore.getState().minimizePanel()

      expect(useSoftphoneStore.getState().panelMinimized).toBe(true)
    })
  })

  describe("expandPanel()", () => {
    it("sets panelMinimized to false and panelOpen to true", () => {
      useSoftphoneStore.setState({ panelOpen: false, panelMinimized: true })
      useSoftphoneStore.getState().expandPanel()

      expect(useSoftphoneStore.getState().panelOpen).toBe(true)
      expect(useSoftphoneStore.getState().panelMinimized).toBe(false)
    })
  })
})
