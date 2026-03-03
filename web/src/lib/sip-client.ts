import {
  UserAgent,
  Registerer,
  RegistererState,
  Inviter,
  Invitation,
  Session,
  SessionState,
  URI,
} from "sip.js"
import type { UserAgentOptions, SessionDescriptionHandlerModifier } from "sip.js"
import {
  SessionDescriptionHandler,
  addMidLines,
} from "sip.js/lib/platform/web"

export type RegistrationStatus = "disconnected" | "connecting" | "registered" | "error"

export interface SipClientConfig {
  wssUrl: string
  sipUsername: string
  sipPassword: string
  sipDomain: string
  displayName: string
}

export interface SipClientEvents {
  onRegistrationStateChanged: (status: RegistrationStatus) => void
  onIncomingCall: (session: Invitation) => void
  onSessionStateChanged: (state: SessionState) => void
}

export class SipClient {
  private ua: UserAgent | null = null
  private registerer: Registerer | null = null
  private session: Session | null = null
  private events: SipClientEvents
  private config: SipClientConfig
  private remoteAudio: HTMLAudioElement | null = null
  // FreeSWITCH omits a=mid: from SDP answers — addMidLines fixes this for Chrome
  private sdpModifiers: SessionDescriptionHandlerModifier[] = [addMidLines]

  constructor(config: SipClientConfig, events: SipClientEvents) {
    this.config = config
    this.events = events
  }

  setRemoteAudio(el: HTMLAudioElement) {
    this.remoteAudio = el
  }

  async connect(): Promise<void> {
    this.events.onRegistrationStateChanged("connecting")

    const uri = UserAgent.makeURI(`sip:${this.config.sipUsername}@${this.config.sipDomain}`)
    if (!uri) throw new Error("Failed to create SIP URI")

    const transportOptions = {
      server: this.config.wssUrl,
    }

    const uaOptions: UserAgentOptions = {
      uri,
      transportOptions,
      authorizationUsername: this.config.sipUsername,
      authorizationPassword: this.config.sipPassword,
      displayName: this.config.displayName,
      sessionDescriptionHandlerFactoryOptions: {
        peerConnectionConfiguration: {
          iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
        },
      },
      delegate: {
        onInvite: (invitation: Invitation) => {
          this.session = invitation
          this._watchSession(invitation)
          this.events.onIncomingCall(invitation)
        },
      },
    }

    this.ua = new UserAgent(uaOptions)

    this.ua.transport.onDisconnect = () => {
      this.events.onRegistrationStateChanged("disconnected")
    }

    await this.ua.start()

    this.registerer = new Registerer(this.ua)

    this.registerer.stateChange.addListener((state: RegistererState) => {
      switch (state) {
        case RegistererState.Registered:
          this.events.onRegistrationStateChanged("registered")
          break
        case RegistererState.Unregistered:
          this.events.onRegistrationStateChanged("disconnected")
          break
        case RegistererState.Terminated:
          this.events.onRegistrationStateChanged("disconnected")
          break
      }
    })

    await this.registerer.register()
  }

  async disconnect(): Promise<void> {
    if (this.session && this.session.state !== SessionState.Terminated) {
      try {
        await this.hangup()
      } catch {
        // ignore cleanup errors
      }
    }
    if (this.registerer) {
      try {
        await this.registerer.unregister()
      } catch {
        // ignore
      }
    }
    if (this.ua) {
      try {
        await this.ua.stop()
      } catch {
        // ignore
      }
    }
    this.ua = null
    this.registerer = null
    this.session = null
  }

  async makeCall(target: string): Promise<void> {
    if (!this.ua) throw new Error("Not connected")

    const targetUri = UserAgent.makeURI(`sip:${target}@${this.config.sipDomain}`)
    if (!targetUri) throw new Error("Invalid target")

    const inviter = new Inviter(this.ua, targetUri, {
      sessionDescriptionHandlerOptions: {
        constraints: { audio: true, video: false },
      },
      sessionDescriptionHandlerModifiers: this.sdpModifiers,
    })

    this.session = inviter
    this._watchSession(inviter)
    await inviter.invite()
  }

  async answerCall(): Promise<void> {
    if (!this.session || !(this.session instanceof Invitation)) {
      throw new Error("No incoming call to answer")
    }
    await (this.session as Invitation).accept({
      sessionDescriptionHandlerOptions: {
        constraints: { audio: true, video: false },
      },
      sessionDescriptionHandlerModifiers: this.sdpModifiers,
    })
  }

  async declineCall(): Promise<void> {
    if (!this.session || !(this.session instanceof Invitation)) {
      throw new Error("No incoming call to decline")
    }
    await (this.session as Invitation).reject()
    this.session = null
  }

  async hangup(): Promise<void> {
    if (!this.session) return

    switch (this.session.state) {
      case SessionState.Initial:
      case SessionState.Establishing:
        if (this.session instanceof Inviter) {
          await this.session.cancel()
        } else if (this.session instanceof Invitation) {
          await this.session.reject()
        }
        break
      case SessionState.Established:
        await this.session.bye()
        break
      default:
        break
    }
    this.session = null
  }

  toggleMute(): boolean {
    if (!this.session) return false
    const sdh = this.session.sessionDescriptionHandler as SessionDescriptionHandler | undefined
    if (!sdh?.peerConnection) return false

    const pc = sdh.peerConnection
    const senders = pc.getSenders()
    const audioSender = senders.find((s) => s.track?.kind === "audio")
    if (audioSender?.track) {
      audioSender.track.enabled = !audioSender.track.enabled
      return !audioSender.track.enabled // true = muted
    }
    return false
  }

  async toggleHold(): Promise<boolean> {
    if (!this.session) return false
    const sdh = this.session.sessionDescriptionHandler as SessionDescriptionHandler | undefined
    if (!sdh?.peerConnection) return false

    const pc = sdh.peerConnection
    const transceivers = pc.getTransceivers()
    const audioTransceiver = transceivers.find(
      (t) => t.sender.track?.kind === "audio" || t.receiver.track?.kind === "audio"
    )

    if (!audioTransceiver) return false

    const isOnHold = audioTransceiver.direction === "sendonly" || audioTransceiver.direction === "inactive"
    audioTransceiver.direction = isOnHold ? "sendrecv" : "sendonly"

    // re-INVITE to signal hold/unhold
    const options = {
      requestDelegate: {
        onAccept: () => {},
        onReject: () => {},
      },
    }
    // Use session.sessionDescriptionHandlerModifiersReInvite for proper re-INVITE
    await this.session.invite(options)

    return !isOnHold // true = now on hold
  }

  sendDTMF(tone: string): void {
    if (!this.session || this.session.state !== SessionState.Established) return

    const options = {
      requestOptions: {
        body: {
          contentDisposition: "render",
          contentType: "application/dtmf-relay",
          content: `Signal=${tone}\r\nDuration=100`,
        },
      },
    }
    this.session.info(options)
  }

  getSession(): Session | null {
    return this.session
  }

  getRemoteIdentity(): string {
    if (!this.session) return ""

    let uri: URI | undefined
    if (this.session instanceof Invitation) {
      uri = this.session.remoteIdentity.uri
    } else if (this.session instanceof Inviter) {
      uri = (this.session as Inviter).remoteIdentity.uri
    }

    if (uri) {
      return uri.user || uri.toString()
    }
    return ""
  }

  private _watchSession(session: Session): void {
    session.stateChange.addListener((state: SessionState) => {
      this.events.onSessionStateChanged(state)

      if (state === SessionState.Established) {
        this._attachRemoteAudio(session)
        this._monitorIceState(session)
      }
      if (state === SessionState.Terminated) {
        this.session = null
      }
    })
  }

  private _monitorIceState(session: Session): void {
    const sdh = session.sessionDescriptionHandler as SessionDescriptionHandler | undefined
    if (!sdh?.peerConnection) return

    const pc = sdh.peerConnection
    console.log(`[WebRTC] ICE state: ${pc.iceConnectionState}, gathering: ${pc.iceGatheringState}`)
    console.log(`[WebRTC] Connection state: ${pc.connectionState}`)
    console.log(`[WebRTC] Signaling state: ${pc.signalingState}`)

    // Log senders/receivers
    const senders = pc.getSenders()
    const receivers = pc.getReceivers()
    senders.forEach((s, i) => {
      console.log(`[WebRTC] Sender[${i}]: kind=${s.track?.kind} enabled=${s.track?.enabled} readyState=${s.track?.readyState} muted=${s.track?.muted}`)
    })
    receivers.forEach((r, i) => {
      console.log(`[WebRTC] Receiver[${i}]: kind=${r.track?.kind} readyState=${r.track?.readyState}`)
    })

    // Log transceivers
    const transceivers = pc.getTransceivers()
    transceivers.forEach((t, i) => {
      console.log(`[WebRTC] Transceiver[${i}]: mid=${t.mid} direction=${t.direction} currentDirection=${t.currentDirection}`)
    })

    pc.oniceconnectionstatechange = () => {
      console.log(`[WebRTC] ICE state changed: ${pc.iceConnectionState}`)
    }
    pc.onconnectionstatechange = () => {
      console.log(`[WebRTC] Connection state changed: ${pc.connectionState}`)
    }

    // Log stats every 2 seconds for debugging
    const statsInterval = setInterval(async () => {
      if (pc.connectionState === "closed" || !this.session) {
        clearInterval(statsInterval)
        return
      }
      try {
        const stats = await pc.getStats()
        stats.forEach((report) => {
          if (report.type === "outbound-rtp" && report.kind === "audio") {
            console.log(`[WebRTC] Outbound audio: packets=${report.packetsSent} bytes=${report.bytesSent}`)
          }
          if (report.type === "inbound-rtp" && report.kind === "audio") {
            console.log(`[WebRTC] Inbound audio: packets=${report.packetsReceived} bytes=${report.bytesReceived}`)
          }
          if (report.type === "candidate-pair" && report.nominated) {
            console.log(`[WebRTC] Active pair: state=${report.state} local=${report.localCandidateId} remote=${report.remoteCandidateId}`)
          }
        })
      } catch {
        clearInterval(statsInterval)
      }
    }, 2000)
  }

  private _attachRemoteAudio(session: Session): void {
    if (!this.remoteAudio) return

    const sdh = session.sessionDescriptionHandler as SessionDescriptionHandler | undefined
    if (!sdh?.peerConnection) return

    const pc = sdh.peerConnection
    const remoteStream = new MediaStream()
    pc.getReceivers().forEach((receiver) => {
      if (receiver.track) {
        remoteStream.addTrack(receiver.track)
      }
    })
    this.remoteAudio.srcObject = remoteStream
    this.remoteAudio.play().catch(() => {
      // autoplay may be blocked — user gesture will resolve
    })
  }
}
