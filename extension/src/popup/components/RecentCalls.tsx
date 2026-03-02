import { useState, useEffect, useCallback } from "preact/hooks"
import type { ExtMessage, MessageResponse, NumberHistoryEntry } from "@/shared/types"
import { formatPhoneNumber } from "@/shared/phone-regex"

function sendMessage(msg: ExtMessage): Promise<MessageResponse> {
  return chrome.runtime.sendMessage(msg)
}

function timeAgo(dateStr: string): string {
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diffSec = Math.floor((now - then) / 1000)
  if (diffSec < 60) return "just now"
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDays = Math.floor(diffHr / 24)
  if (diffDays < 7) return `${diffDays}d ago`
  return new Date(dateStr).toLocaleDateString()
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const min = Math.floor(seconds / 60)
  const sec = seconds % 60
  return sec > 0 ? `${min}m ${sec}s` : `${min}m`
}

function DirectionIcon({ direction }: { direction: string }) {
  const isInbound = direction === "inbound"
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      style={{ flexShrink: 0, marginTop: "2px" }}
    >
      {isInbound ? (
        <path
          d="M10 2L4 8M4 8V3M4 8H9"
          stroke="#16a34a"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      ) : (
        <path
          d="M4 12L10 6M10 6V11M10 6H5"
          stroke="#2563eb"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      )}
    </svg>
  )
}

export function RecentCalls({
  onCallBack,
}: {
  onCallBack: (number: string) => void
}) {
  const [calls, setCalls] = useState<NumberHistoryEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const fetchCalls = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const resp = await sendMessage({ type: "GET_RECENT_CALLS" })
      if (resp.success && Array.isArray(resp.data)) {
        setCalls(resp.data as NumberHistoryEntry[])
      } else {
        setError(resp.error || "Failed to load calls")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load calls")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchCalls()
  }, [fetchCalls])

  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={headerStyle}>Recent Calls</div>
        <div style={emptyStyle}>Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={containerStyle}>
        <div style={headerStyle}>Recent Calls</div>
        <div style={{ ...emptyStyle, color: "#dc2626" }}>{error}</div>
      </div>
    )
  }

  if (calls.length === 0) {
    return (
      <div style={containerStyle}>
        <div style={headerStyle}>Recent Calls</div>
        <div style={emptyStyle}>No recent calls</div>
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>Recent Calls</div>
      <div style={{ display: "flex", flexDirection: "column", gap: "1px" }}>
        {calls.map((call) => {
          const isInbound = call.direction === "inbound"
          const displayNumber = isInbound ? call.caller_number : call.called_number
          const displayName = isInbound
            ? call.caller_name
            : call.called_number
          const formattedNumber = formatPhoneNumber(displayNumber)

          return (
            <button
              key={call.id}
              onClick={() => onCallBack(displayNumber)}
              style={callRowStyle}
              title={`Call ${formattedNumber}`}
            >
              <DirectionIcon direction={call.direction} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={callNameStyle}>
                  {call.caller_name && isInbound
                    ? call.caller_name
                    : formattedNumber}
                </div>
                {call.caller_name && isInbound && (
                  <div style={callNumberStyle}>{formattedNumber}</div>
                )}
              </div>
              <div style={callMetaStyle}>
                <div>{timeAgo(call.start_time)}</div>
                <div style={{ color: "#94a3b8" }}>
                  {formatDuration(call.duration_seconds)}
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

// --- Styles ---

const containerStyle: Record<string, string> = {
  marginTop: "8px",
}

const headerStyle: Record<string, string> = {
  fontSize: "11px",
  fontWeight: "600",
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  color: "#94a3b8",
  padding: "0 0 6px",
}

const emptyStyle: Record<string, string> = {
  textAlign: "center",
  color: "#94a3b8",
  fontSize: "13px",
  padding: "20px 0",
}

const callRowStyle: Record<string, string | number> = {
  display: "flex",
  alignItems: "flex-start",
  gap: "8px",
  padding: "8px 6px",
  border: "none",
  borderRadius: "6px",
  background: "transparent",
  cursor: "pointer",
  textAlign: "left",
  width: "100%",
  fontSize: "13px",
  fontFamily: "inherit",
  color: "inherit",
  transition: "background-color 0.1s ease",
}

const callNameStyle: Record<string, string> = {
  fontWeight: "500",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
}

const callNumberStyle: Record<string, string> = {
  fontSize: "11px",
  color: "#94a3b8",
  marginTop: "1px",
}

const callMetaStyle: Record<string, string> = {
  textAlign: "right",
  fontSize: "11px",
  color: "#64748b",
  flexShrink: "0",
  whiteSpace: "nowrap",
}
