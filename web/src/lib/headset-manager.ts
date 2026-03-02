import HeadsetService, { HeadsetEvents } from "softphone-vendor-headsets"
import type { ConsumedHeadsetEvents } from "softphone-vendor-headsets"
import type { Subscription } from "rxjs"
import { useHeadsetStore } from "@/stores/headset-store"
import { useSoftphoneStore, type CallState } from "@/stores/softphone-store"

// Stable conversation ID for the current call (headset SDK tracks by conversationId)
let currentConversationId = ""

function nextConversationId(): string {
  currentConversationId = crypto.randomUUID()
  return currentConversationId
}

class HeadsetManager {
  private static instance: HeadsetManager | null = null
  private service: HeadsetService | null = null
  private subscription: Subscription | null = null
  private initialized = false

  // Track last state we sent to headset to avoid duplicate notifications
  private lastNotifiedCallState: CallState = "idle"
  private lastNotifiedMuted = false
  private lastNotifiedHold = false

  private constructor() {}

  static getInstance(): HeadsetManager {
    if (!HeadsetManager.instance) {
      HeadsetManager.instance = new HeadsetManager()
    }
    return HeadsetManager.instance
  }

  initialize(): void {
    if (this.initialized) return

    try {
      this.service = HeadsetService.getInstance({
        logger: console,
        appName: "AspendoraConnect",
      })
    } catch (err) {
      console.warn("[HeadsetManager] Failed to initialize headset SDK:", err)
      useHeadsetStore.getState().setSupported(false)
      return
    }

    this.subscription = this.service.headsetEvents$.subscribe((event) => {
      this.handleHeadsetEvent(event)
    })

    this.initialized = true

    // Check initial connection status
    const status = this.service.connectionStatus()
    if (status === "running") {
      this.updateConnectionState()
    }
  }

  destroy(): void {
    this.subscription?.unsubscribe()
    this.subscription = null
    this.service = null
    this.initialized = false
    this.lastNotifiedCallState = "idle"
    this.lastNotifiedMuted = false
    this.lastNotifiedHold = false
    currentConversationId = ""
    useHeadsetStore.getState().reset()
  }

  /**
   * Called by the useHeadset hook when softphone state changes.
   * Forwards state to the headset SDK so LEDs/ring tones update.
   */
  notifySoftphoneStateChange(
    callState: CallState,
    isMuted: boolean,
    isOnHold: boolean,
    remoteIdentity: string,
  ): void {
    if (!this.service) return

    // Call state transitions → headset notifications
    if (callState !== this.lastNotifiedCallState) {
      this.handleCallStateTransition(this.lastNotifiedCallState, callState, remoteIdentity)
      this.lastNotifiedCallState = callState
    }

    // Mute sync
    if (isMuted !== this.lastNotifiedMuted) {
      this.service.setMute(isMuted).catch(() => {})
      this.lastNotifiedMuted = isMuted
    }

    // Hold sync
    if (isOnHold !== this.lastNotifiedHold && currentConversationId) {
      this.service.setHold(currentConversationId, isOnHold).catch(() => {})
      this.lastNotifiedHold = isOnHold
    }
  }

  private handleCallStateTransition(
    prev: CallState,
    next: CallState,
    remoteIdentity: string,
  ): void {
    if (!this.service) return

    // Entering a call state
    if (next === "ringing_in") {
      const id = nextConversationId()
      this.service.incomingCall({ conversationId: id, contactName: remoteIdentity }).catch(() => {})
    } else if (next === "ringing_out") {
      const id = nextConversationId()
      this.service.outgoingCall({ conversationId: id, contactName: remoteIdentity }).catch(() => {})
    } else if (next === "connected" && (prev === "ringing_in" || prev === "ringing_out")) {
      this.service.answerCall(currentConversationId).catch(() => {})
    } else if (next === "idle" && prev !== "idle") {
      if (currentConversationId) {
        this.service.endCall(currentConversationId).catch(() => {})
      }
      currentConversationId = ""
      this.lastNotifiedMuted = false
      this.lastNotifiedHold = false
    }
  }

  private handleHeadsetEvent(event: ConsumedHeadsetEvents): void {
    const store = useSoftphoneStore.getState()

    switch (event.event) {
      case HeadsetEvents.deviceAnsweredCall:
        if (store.callState === "ringing_in") {
          store.answerCall()
        }
        break

      case HeadsetEvents.deviceRejectedCall:
        if (store.callState === "ringing_in") {
          store.declineCall()
        }
        break

      case HeadsetEvents.deviceEndedCall:
        if (store.callState !== "idle") {
          store.hangup()
        }
        break

      case HeadsetEvents.deviceMuteStatusChanged: {
        const { isMuted } = event.payload
        if (isMuted !== store.isMuted) {
          store.toggleMute()
        }
        this.lastNotifiedMuted = isMuted
        break
      }

      case HeadsetEvents.deviceHoldStatusChanged: {
        const { holdRequested } = event.payload
        if (holdRequested !== store.isOnHold) {
          store.toggleHold()
        }
        this.lastNotifiedHold = holdRequested
        break
      }

      case HeadsetEvents.deviceConnectionStatusChanged:
        this.updateConnectionState()
        break

      case HeadsetEvents.implementationChanged:
        this.updateConnectionState()
        break

      case HeadsetEvents.webHidPermissionRequested:
        // The SDK provides a callback to trigger the WebHID permission prompt.
        // Call it so the browser shows the device picker.
        if (event.payload?.callback) {
          event.payload.callback()
        }
        break
    }
  }

  private updateConnectionState(): void {
    if (!this.service) return

    const impl = this.service.selectedImplementation
    if (impl?.isConnected) {
      const deviceName = impl.deviceInfo?.ProductName
        ?? impl.deviceInfo?.deviceName
        ?? null
      useHeadsetStore.getState().setConnected(true, deviceName, impl.vendorName || null)
    } else {
      useHeadsetStore.getState().setConnected(false)
    }
  }

  /**
   * Let the headset SDK know which mic is active so it can auto-select the right vendor.
   */
  activeMicChange(micLabel: string): void {
    if (!this.service) return
    this.service.activeMicChange(micLabel)
  }
}

export const headsetManager = HeadsetManager.getInstance()
