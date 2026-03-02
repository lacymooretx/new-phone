import { useState, useEffect, useCallback } from "preact/hooks"
import type {
  ExtMessage,
  MessageResponse,
  AuthState,
  LoginPayload,
  MfaPayload,
  ExtensionSettings,
} from "@/shared/types"

function sendMessage(msg: ExtMessage): Promise<MessageResponse> {
  return chrome.runtime.sendMessage(msg)
}

export function LoginForm({
  onLogin,
}: {
  onLogin: (state: AuthState) => void
}) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [apiUrl, setApiUrl] = useState("")
  const [mfaCode, setMfaCode] = useState("")
  const [mfaRequired, setMfaRequired] = useState(false)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    sendMessage({ type: "GET_SETTINGS" }).then((resp) => {
      if (resp.success && resp.data) {
        setApiUrl((resp.data as ExtensionSettings).apiBaseUrl || "")
      }
    })
  }, [])

  const handleLogin = useCallback(
    async (e: Event) => {
      e.preventDefault()
      setError("")
      setLoading(true)
      try {
        const resp = await sendMessage({
          type: "AUTH_LOGIN",
          payload: {
            email,
            password,
            apiBaseUrl: apiUrl,
          } satisfies LoginPayload,
        })
        if (resp.success) {
          const state = resp.data as AuthState
          if (state.mfaRequired) {
            setMfaRequired(true)
          } else {
            onLogin(state)
          }
        } else {
          setError(resp.error || "Login failed")
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        setLoading(false)
      }
    },
    [email, password, apiUrl, onLogin],
  )

  const handleMfa = useCallback(
    async (e: Event) => {
      e.preventDefault()
      setError("")
      setLoading(true)
      try {
        const resp = await sendMessage({
          type: "AUTH_MFA_COMPLETE",
          payload: { code: mfaCode } satisfies MfaPayload,
        })
        if (resp.success) {
          onLogin(resp.data as AuthState)
        } else {
          setError(resp.error || "Verification failed")
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        setLoading(false)
      }
    },
    [mfaCode, onLogin],
  )

  // MFA code input screen
  if (mfaRequired) {
    return (
      <form onSubmit={handleMfa} style={formStyle}>
        <div style={logoSectionStyle}>
          <div style={logoStyle}>NP</div>
          <h2 style={titleStyle}>Verification Required</h2>
          <p style={subtitleStyle}>Enter the code from your authenticator app</p>
        </div>

        {error && <div style={errorStyle}>{error}</div>}

        <label style={labelStyle}>
          Verification Code
          <input
            type="text"
            value={mfaCode}
            onInput={(e) => setMfaCode((e.target as HTMLInputElement).value)}
            placeholder="123456"
            required
            autocomplete="one-time-code"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={6}
            style={inputStyle}
            autofocus
          />
        </label>

        <button type="submit" disabled={loading} style={btnPrimaryStyle}>
          {loading ? (
            <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}>
              <Spinner />
              Verifying...
            </span>
          ) : (
            "Verify"
          )}
        </button>

        <button
          type="button"
          onClick={() => {
            setMfaRequired(false)
            setMfaCode("")
            setError("")
          }}
          style={linkBtnStyle}
        >
          Back to Sign In
        </button>
      </form>
    )
  }

  return (
    <form onSubmit={handleLogin} style={formStyle}>
      <div style={logoSectionStyle}>
        <div style={logoStyle}>NP</div>
        <h2 style={titleStyle}>Sign In</h2>
        <p style={subtitleStyle}>Connect to your New Phone server</p>
      </div>

      {error && <div style={errorStyle}>{error}</div>}

      <label style={labelStyle}>
        Server URL
        <input
          type="url"
          value={apiUrl}
          onInput={(e) => setApiUrl((e.target as HTMLInputElement).value)}
          placeholder="https://phone.example.com"
          required
          style={inputStyle}
        />
      </label>

      <label style={labelStyle}>
        Email
        <input
          type="email"
          value={email}
          onInput={(e) => setEmail((e.target as HTMLInputElement).value)}
          required
          style={inputStyle}
        />
      </label>

      <label style={labelStyle}>
        Password
        <input
          type="password"
          value={password}
          onInput={(e) => setPassword((e.target as HTMLInputElement).value)}
          required
          style={inputStyle}
        />
      </label>

      <button type="submit" disabled={loading} style={btnPrimaryStyle}>
        {loading ? (
          <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}>
            <Spinner />
            Signing in...
          </span>
        ) : (
          "Sign In"
        )}
      </button>
    </form>
  )
}

function Spinner() {
  return (
    <>
      <svg
        width="14"
        height="14"
        viewBox="0 0 14 14"
        fill="none"
        style={{ animation: "np-spin 0.8s linear infinite" }}
      >
        <circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-opacity="0.25" stroke-width="2" />
        <path
          d="M12.5 7a5.5 5.5 0 00-5.5-5.5"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        />
      </svg>
      <style>{`
        @keyframes np-spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </>
  )
}

// --- Styles ---

const formStyle: Record<string, string> = {
  padding: "20px 16px 16px",
}

const logoSectionStyle: Record<string, string> = {
  textAlign: "center",
  marginBottom: "16px",
}

const logoStyle: Record<string, string> = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: "40px",
  height: "40px",
  borderRadius: "10px",
  background: "#2563eb",
  color: "#ffffff",
  fontSize: "16px",
  fontWeight: "700",
  marginBottom: "8px",
}

const titleStyle: Record<string, string> = {
  margin: "0",
  fontSize: "16px",
  fontWeight: "600",
}

const subtitleStyle: Record<string, string> = {
  margin: "4px 0 0",
  fontSize: "12px",
  color: "#64748b",
}

const errorStyle: Record<string, string> = {
  color: "#dc2626",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  borderRadius: "6px",
  padding: "8px 10px",
  fontSize: "12px",
  marginBottom: "12px",
}

const labelStyle: Record<string, string> = {
  display: "block",
  marginBottom: "10px",
  fontSize: "12px",
  fontWeight: "500",
  color: "#64748b",
}

const inputStyle: Record<string, string> = {
  display: "block",
  width: "100%",
  padding: "8px 10px",
  marginTop: "4px",
  border: "1px solid #e2e8f0",
  borderRadius: "6px",
  fontSize: "13px",
  outline: "none",
  boxSizing: "border-box",
}

const btnPrimaryStyle: Record<string, string> = {
  display: "block",
  width: "100%",
  padding: "9px 16px",
  marginTop: "4px",
  background: "#2563eb",
  color: "#ffffff",
  border: "none",
  borderRadius: "6px",
  fontSize: "13px",
  fontWeight: "500",
  cursor: "pointer",
}

const linkBtnStyle: Record<string, string> = {
  display: "block",
  width: "100%",
  marginTop: "8px",
  padding: "6px",
  background: "transparent",
  color: "#64748b",
  border: "none",
  fontSize: "12px",
  cursor: "pointer",
  textAlign: "center",
}
