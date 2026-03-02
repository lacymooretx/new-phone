import { create } from "zustand"
import { SessionState, Invitation } from "sip.js"
import { SipClient, type SipClientConfig, type RegistrationStatus } from "@/lib/sip-client"
import { isDesktop, showNativeNotification } from "@/lib/desktop-bridge"

export type CallState = "idle" | "ringing_in" | "ringing_out" | "connected" | "on_hold"
export type CallDirection = "inbound" | "outbound" | null

interface SoftphoneState {
  // Registration
  status: RegistrationStatus
  // Call
  callState: CallState
  callDirection: CallDirection
  remoteIdentity: string
  callStartTime: number | null
  isMuted: boolean
  isOnHold: boolean
  // UI
  panelOpen: boolean
  panelMinimized: boolean

  // Actions
  connect: (config: SipClientConfig, remoteAudio: HTMLAudioElement) => Promise<void>
  disconnect: () => Promise<void>
  makeCall: (target: string) => Promise<void>
  answerCall: () => Promise<void>
  declineCall: () => Promise<void>
  hangup: () => Promise<void>
  toggleMute: () => void
  toggleHold: () => Promise<void>
  sendDTMF: (tone: string) => void
  togglePanel: () => void
  minimizePanel: () => void
  expandPanel: () => void
}

let sipClient: SipClient | null = null

export const useSoftphoneStore = create<SoftphoneState>((set, get) => ({
  status: "disconnected",
  callState: "idle",
  callDirection: null,
  remoteIdentity: "",
  callStartTime: null,
  isMuted: false,
  isOnHold: false,
  panelOpen: false,
  panelMinimized: false,

  connect: async (config, remoteAudio) => {
    if (sipClient) {
      await sipClient.disconnect()
    }

    sipClient = new SipClient(config, {
      onRegistrationStateChanged: (status) => {
        set({ status })
      },
      onIncomingCall: (_invitation: Invitation) => {
        const identity = sipClient?.getRemoteIdentity() || "Unknown"
        set({
          callState: "ringing_in",
          callDirection: "inbound",
          remoteIdentity: identity,
          panelOpen: true,
          panelMinimized: false,
        })
        if (isDesktop()) {
          showNativeNotification("Incoming Call", identity)
        }
      },
      onSessionStateChanged: (state: SessionState) => {
        switch (state) {
          case SessionState.Establishing:
            // Already set during makeCall/incoming
            break
          case SessionState.Established:
            set({
              callState: "connected",
              callStartTime: Date.now(),
              isMuted: false,
              isOnHold: false,
            })
            break
          case SessionState.Terminated:
            set({
              callState: "idle",
              callDirection: null,
              remoteIdentity: "",
              callStartTime: null,
              isMuted: false,
              isOnHold: false,
            })
            break
        }
      },
    })

    sipClient.setRemoteAudio(remoteAudio)
    await sipClient.connect()
  },

  disconnect: async () => {
    if (sipClient) {
      await sipClient.disconnect()
      sipClient = null
    }
    set({
      status: "disconnected",
      callState: "idle",
      callDirection: null,
      remoteIdentity: "",
      callStartTime: null,
      isMuted: false,
      isOnHold: false,
    })
  },

  makeCall: async (target) => {
    if (!sipClient) throw new Error("Not connected")
    set({
      callState: "ringing_out",
      callDirection: "outbound",
      remoteIdentity: target,
      panelOpen: true,
      panelMinimized: false,
    })
    await sipClient.makeCall(target)
  },

  answerCall: async () => {
    if (!sipClient) return
    await sipClient.answerCall()
  },

  declineCall: async () => {
    if (!sipClient) return
    await sipClient.declineCall()
    set({
      callState: "idle",
      callDirection: null,
      remoteIdentity: "",
    })
  },

  hangup: async () => {
    if (!sipClient) return
    await sipClient.hangup()
    set({
      callState: "idle",
      callDirection: null,
      remoteIdentity: "",
      callStartTime: null,
      isMuted: false,
      isOnHold: false,
    })
  },

  toggleMute: () => {
    if (!sipClient) return
    const muted = sipClient.toggleMute()
    set({ isMuted: muted })
  },

  toggleHold: async () => {
    if (!sipClient) return
    const onHold = await sipClient.toggleHold()
    set({
      isOnHold: onHold,
      callState: onHold ? "on_hold" : "connected",
    })
  },

  sendDTMF: (tone) => {
    if (!sipClient) return
    sipClient.sendDTMF(tone)
  },

  togglePanel: () => {
    const { panelOpen, panelMinimized } = get()
    if (!panelOpen) {
      set({ panelOpen: true, panelMinimized: false })
    } else if (!panelMinimized) {
      set({ panelOpen: false })
    } else {
      set({ panelMinimized: false })
    }
  },

  minimizePanel: () => set({ panelMinimized: true }),
  expandPanel: () => set({ panelMinimized: false, panelOpen: true }),
}))
