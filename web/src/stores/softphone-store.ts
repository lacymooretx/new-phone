import { create } from "zustand"
import { SessionState, Invitation } from "sip.js"
import { SipClient, type SipClientConfig, type RegistrationStatus } from "@/lib/sip-client"
import { isDesktop, showNativeNotification } from "@/lib/desktop-bridge"

export type CallState = "idle" | "ringing_in" | "ringing_out" | "connected" | "on_hold"
export type CallDirection = "inbound" | "outbound" | null
export type TransferMode = "idle" | "selecting" | "blind" | "consulting" | "attended"
export type ConsultCallState = "idle" | "ringing" | "connected" | "terminated"

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
  // Transfer
  transferMode: TransferMode
  consultRemoteIdentity: string
  consultCallState: ConsultCallState
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
  setMicDevice: (deviceId: string) => void
  setSpeakerDevice: (deviceId: string) => void
  togglePanel: () => void
  minimizePanel: () => void
  expandPanel: () => void
  // Transfer actions
  startTransfer: () => void
  cancelTransfer: () => void
  blindTransfer: (target: string) => Promise<void>
  startConsultTransfer: (target: string) => Promise<void>
  completeAttendedTransfer: () => Promise<void>
  cancelConsult: () => Promise<void>
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
  transferMode: "idle",
  consultRemoteIdentity: "",
  consultCallState: "idle",
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
              transferMode: "idle",
              consultRemoteIdentity: "",
              consultCallState: "idle",
            })
            break
        }
      },
      onConsultSessionStateChanged: (state: SessionState) => {
        switch (state) {
          case SessionState.Establishing:
            set({ consultCallState: "ringing" })
            break
          case SessionState.Established:
            set({
              consultCallState: "connected",
              transferMode: "attended",
              consultRemoteIdentity: sipClient?.getConsultRemoteIdentity() || "",
            })
            break
          case SessionState.Terminated:
            set({ consultCallState: "idle", consultRemoteIdentity: "" })
            // If we were consulting, revert transfer mode
            if (get().transferMode === "consulting" || get().transferMode === "attended") {
              set({ transferMode: "idle" })
            }
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
      transferMode: "idle",
      consultRemoteIdentity: "",
      consultCallState: "idle",
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
      transferMode: "idle",
      consultRemoteIdentity: "",
      consultCallState: "idle",
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

  setMicDevice: (deviceId: string) => {
    if (sipClient) sipClient.setMicDevice(deviceId)
  },

  setSpeakerDevice: (deviceId: string) => {
    if (sipClient) sipClient.setSpeakerDevice(deviceId)
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

  // Transfer actions
  startTransfer: () => set({ transferMode: "selecting" }),
  cancelTransfer: () => set({ transferMode: "idle" }),

  blindTransfer: async (target) => {
    if (!sipClient) return
    set({ transferMode: "blind" })
    try {
      await sipClient.blindTransfer(target)
      set({
        callState: "idle",
        callDirection: null,
        remoteIdentity: "",
        callStartTime: null,
        isMuted: false,
        isOnHold: false,
        transferMode: "idle",
      })
    } catch {
      set({ transferMode: "selecting" })
    }
  },

  startConsultTransfer: async (target) => {
    if (!sipClient) return
    set({ transferMode: "consulting", consultRemoteIdentity: target })
    try {
      await sipClient.makeConsultCall(target)
    } catch {
      set({ transferMode: "selecting", consultRemoteIdentity: "", consultCallState: "idle" })
    }
  },

  completeAttendedTransfer: async () => {
    if (!sipClient) return
    try {
      await sipClient.completeAttendedTransfer()
      set({
        callState: "idle",
        callDirection: null,
        remoteIdentity: "",
        callStartTime: null,
        isMuted: false,
        isOnHold: false,
        transferMode: "idle",
        consultRemoteIdentity: "",
        consultCallState: "idle",
      })
    } catch {
      // stay in attended mode if transfer fails
    }
  },

  cancelConsult: async () => {
    if (!sipClient) return
    try {
      await sipClient.cancelConsult()
    } catch {
      // ignore
    }
    set({
      transferMode: "idle",
      consultRemoteIdentity: "",
      consultCallState: "idle",
      isOnHold: false,
      callState: "connected",
    })
  },
}))
