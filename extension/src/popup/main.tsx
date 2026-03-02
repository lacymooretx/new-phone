import { render } from "preact"
import { useState, useEffect, useCallback } from "preact/hooks"
import type {
  ExtMessage,
  MessageResponse,
  AuthState,
  AppError,
} from "@/shared/types"
import { LoginForm } from "./components/LoginForm"
import { CallStatus } from "./components/CallStatus"
import { RecentCalls } from "./components/RecentCalls"
import { ErrorBanner } from "./components/ErrorBanner"

function sendMessage(msg: ExtMessage): Promise<MessageResponse> {
  return chrome.runtime.sendMessage(msg)
}

// --- Authenticated view ---
function AuthenticatedView({
  auth,
  onLogout,
  error,
  onDismissError,
  onRetry,
}: {
  auth: AuthState
  onLogout: () => void
  error: AppError | null
  onDismissError: () => void
  onRetry: () => void
}) {
  const [destination, setDestination] = useState("")

  const handleCall = useCallback(
    async (number?: string) => {
      const target = number || destination.trim()
      if (!target) return
      await sendMessage({
        type: "INITIATE_CALL",
        payload: { destination: target },
      })
      if (!number) setDestination("")
    },
    [destination],
  )

  const openWebClient = useCallback(() => {
    sendMessage({ type: "OPEN_WEB_CLIENT" })
  }, [])

  const openSettings = useCallback(() => {
    chrome.runtime.openOptionsPage()
  }, [])

  return (
    <div style={{ padding: "12px 14px 14px" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "10px",
        }}
      >
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: "14px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {auth.user?.display_name || "User"}
          </div>
          <div style={{ fontSize: "11px", color: "#64748b" }}>
            Ext. {auth.user?.extension_number || "N/A"}
          </div>
        </div>
        <div style={{ display: "flex", gap: "4px", flexShrink: 0 }}>
          <button onClick={openSettings} style={btnIconStyle} title="Settings">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path
                d="M5.73 1.68a1.27 1.27 0 012.54 0 1.27 1.27 0 001.89.83 1.27 1.27 0 011.8 1.8 1.27 1.27 0 00.83 1.89 1.27 1.27 0 010 2.54 1.27 1.27 0 00-.83 1.89 1.27 1.27 0 01-1.8 1.8 1.27 1.27 0 00-1.89.83 1.27 1.27 0 01-2.54 0 1.27 1.27 0 00-1.89-.83 1.27 1.27 0 01-1.8-1.8 1.27 1.27 0 00-.83-1.89 1.27 1.27 0 010-2.54 1.27 1.27 0 00.83-1.89 1.27 1.27 0 011.8-1.8 1.27 1.27 0 001.89-.83z"
                stroke="#64748b"
                stroke-width="1.1"
              />
              <circle cx="7" cy="7" r="1.8" stroke="#64748b" stroke-width="1.1" />
            </svg>
          </button>
          <button onClick={onLogout} style={btnIconStyle} title="Sign out">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path
                d="M9 1.5H11a1.5 1.5 0 011.5 1.5v9a1.5 1.5 0 01-1.5 1.5H9M5 10l3-3-3-3M12 7H3"
                stroke="#64748b"
                stroke-width="1.1"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <ErrorBanner
          error={error}
          onDismiss={onDismissError}
          onRetry={onRetry}
          onRelogin={onLogout}
        />
      )}

      {/* Active call indicator */}
      <CallStatus />

      {/* Dial box */}
      <div style={{ marginBottom: "8px" }}>
        <div style={{ display: "flex", gap: "4px" }}>
          <input
            type="tel"
            value={destination}
            onInput={(e) =>
              setDestination((e.target as HTMLInputElement).value)
            }
            placeholder="Enter number to call"
            style={{ ...inputStyle, flex: "1" }}
            onKeyDown={(e) => e.key === "Enter" && handleCall()}
          />
          <button onClick={() => handleCall()} style={btnCallStyle} title="Call">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path
                d="M5.55 2.08l-.78-.78a1.37 1.37 0 00-1.94 0L1.95 2.18a1.92 1.92 0 00-.3 2.3 18.9 18.9 0 003.6 4.27 18.9 18.9 0 004.27 3.6 1.92 1.92 0 002.3-.3l.88-.88a1.37 1.37 0 000-1.94l-.78-.78a1.37 1.37 0 00-1.94 0l-.22.22a.46.46 0 01-.54.08 13.4 13.4 0 01-2.52-1.78 13.4 13.4 0 01-1.78-2.52.46.46 0 01.08-.54l.22-.22a1.37 1.37 0 000-1.94z"
                fill="#ffffff"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Quick actions */}
      <button onClick={openWebClient} style={btnWebClientStyle}>
        Open Web Client
      </button>

      {/* Recent calls */}
      <RecentCalls onCallBack={(num) => handleCall(num)} />
    </div>
  )
}

// --- Main App ---
function App() {
  const [auth, setAuth] = useState<AuthState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<AppError | null>(null)

  const checkAuthStatus = useCallback(async () => {
    try {
      const resp = await sendMessage({ type: "AUTH_STATUS" })
      if (resp.success) {
        const state = resp.data as AuthState
        setAuth(state)
        if (state.isAuthenticated) {
          setError(null)
        }
      } else {
        setError({
          type: "connection",
          message: "Unable to check authentication status.",
          dismissible: true,
        })
      }
    } catch {
      setError({
        type: "server_unreachable",
        message: "Extension service worker is unavailable.",
        dismissible: false,
      })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    checkAuthStatus()
  }, [checkAuthStatus])

  const handleLogout = useCallback(async () => {
    await sendMessage({ type: "AUTH_LOGOUT" })
    setAuth({ isAuthenticated: false })
    setError(null)
  }, [])

  const handleLogin = useCallback((state: AuthState) => {
    setAuth(state)
    setError(null)
  }, [])

  if (loading) {
    return (
      <div style={{ padding: "40px 16px", textAlign: "center", color: "#94a3b8" }}>
        <div style={{ marginBottom: "8px" }}>
          <svg
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="none"
            style={{ animation: "np-spin 0.8s linear infinite" }}
          >
            <circle cx="10" cy="10" r="8" stroke="#e2e8f0" stroke-width="2.5" />
            <path
              d="M18 10a8 8 0 00-8-8"
              stroke="#2563eb"
              stroke-width="2.5"
              stroke-linecap="round"
            />
          </svg>
          <style>{`
            @keyframes np-spin {
              to { transform: rotate(360deg); }
            }
          `}</style>
        </div>
        Loading...
      </div>
    )
  }

  if (!auth?.isAuthenticated) {
    return <LoginForm onLogin={handleLogin} />
  }

  return (
    <AuthenticatedView
      auth={auth}
      onLogout={handleLogout}
      error={error}
      onDismissError={() => setError(null)}
      onRetry={checkAuthStatus}
    />
  )
}

// --- Styles ---

const inputStyle: Record<string, string> = {
  display: "block",
  width: "100%",
  padding: "8px 10px",
  border: "1px solid #e2e8f0",
  borderRadius: "6px",
  fontSize: "13px",
  outline: "none",
  boxSizing: "border-box",
}

const btnCallStyle: Record<string, string> = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "8px 12px",
  background: "#16a34a",
  color: "#ffffff",
  border: "none",
  borderRadius: "6px",
  cursor: "pointer",
  flexShrink: "0",
}

const btnWebClientStyle: Record<string, string> = {
  display: "block",
  width: "100%",
  padding: "7px 12px",
  background: "#f1f5f9",
  color: "#334155",
  border: "1px solid #e2e8f0",
  borderRadius: "6px",
  fontSize: "12px",
  fontWeight: "500",
  cursor: "pointer",
  textAlign: "center",
  fontFamily: "inherit",
}

const btnIconStyle: Record<string, string> = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "4px",
  background: "transparent",
  border: "1px solid #e2e8f0",
  borderRadius: "4px",
  cursor: "pointer",
}

// --- Mount ---
render(<App />, document.getElementById("app")!)
