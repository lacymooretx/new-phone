import { useState, useEffect, useRef } from "preact/hooks"
import type { ActiveCallInfo, ExtMessage, MessageResponse } from "@/shared/types"
import { formatPhoneNumber } from "@/shared/phone-regex"

function sendMessage(msg: ExtMessage): Promise<MessageResponse> {
  return chrome.runtime.sendMessage(msg)
}

function formatTimer(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  const mm = String(m).padStart(2, "0")
  const ss = String(s).padStart(2, "0")
  if (h > 0) return `${h}:${mm}:${ss}`
  return `${m}:${ss}`
}

export function CallStatus() {
  const [call, setCall] = useState<ActiveCallInfo | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Poll for active call every 2 seconds
  useEffect(() => {
    let active = true

    async function poll() {
      try {
        const resp = await sendMessage({ type: "GET_ACTIVE_CALL" })
        if (!active) return
        if (resp.success && resp.data) {
          setCall(resp.data as ActiveCallInfo)
        } else {
          setCall(null)
        }
      } catch {
        if (active) setCall(null)
      }
    }

    poll()
    const interval = setInterval(poll, 2000)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [])

  // Elapsed timer
  useEffect(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }

    if (call?.state === "connected" && call.started_at) {
      const start = new Date(call.started_at).getTime()

      function tick() {
        const now = Date.now()
        setElapsed(Math.floor((now - start) / 1000))
      }

      tick()
      timerRef.current = setInterval(tick, 1000)
    } else {
      setElapsed(0)
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [call?.state, call?.started_at])

  if (!call || call.state === "idle") {
    return null
  }

  const isRinging = call.state === "ringing"
  const isConnected = call.state === "connected"
  const isOnHold = call.state === "on_hold"

  const remoteName = call.remote_name || formatPhoneNumber(call.remote_number)
  const dirLabel = call.direction === "inbound" ? "Incoming" : "Outgoing"

  return (
    <div style={wrapperStyle}>
      <div style={callCardStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {/* Pulsing dot */}
          <span
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              background: isRinging
                ? "#eab308"
                : isOnHold
                  ? "#f97316"
                  : "#22c55e",
              display: "inline-block",
              flexShrink: 0,
              animation: isRinging ? "np-pulse 1.2s ease-in-out infinite" : "none",
            }}
          />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={callLabelStyle}>
              {isRinging
                ? `${dirLabel} call - Ringing`
                : isOnHold
                  ? "On Hold"
                  : "Connected"}
            </div>
            <div style={callRemoteStyle}>{remoteName}</div>
          </div>
          {isConnected && (
            <div style={timerStyle}>{formatTimer(elapsed)}</div>
          )}
        </div>
      </div>
      <style>{`
        @keyframes np-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(1.3); }
        }
      `}</style>
    </div>
  )
}

// --- Styles ---

const wrapperStyle: Record<string, string> = {
  marginBottom: "8px",
}

const callCardStyle: Record<string, string> = {
  padding: "10px 12px",
  background: "#f0fdf4",
  border: "1px solid #bbf7d0",
  borderRadius: "8px",
}

const callLabelStyle: Record<string, string> = {
  fontSize: "11px",
  fontWeight: "500",
  color: "#64748b",
  textTransform: "uppercase",
  letterSpacing: "0.3px",
}

const callRemoteStyle: Record<string, string> = {
  fontSize: "14px",
  fontWeight: "600",
  color: "#1a202c",
  marginTop: "1px",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
}

const timerStyle: Record<string, string> = {
  fontSize: "16px",
  fontWeight: "600",
  fontVariantNumeric: "tabular-nums",
  color: "#16a34a",
  flexShrink: "0",
}
