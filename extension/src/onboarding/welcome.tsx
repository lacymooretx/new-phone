import { render } from "preact"
import { useState, useCallback } from "preact/hooks"
import type { ExtMessage, MessageResponse, AuthState, LoginPayload, ExtensionSettings } from "@/shared/types"
import { apiHealthCheck } from "@/shared/api"

function sendMessage(msg: ExtMessage): Promise<MessageResponse> {
  return chrome.runtime.sendMessage(msg)
}

type WizardStep = "welcome" | "server" | "login" | "test" | "done"

const STEPS: WizardStep[] = ["welcome", "server", "login", "test", "done"]

function ProgressBar({ current }: { current: WizardStep }) {
  const idx = STEPS.indexOf(current)
  const pct = Math.round((idx / (STEPS.length - 1)) * 100)
  return (
    <div style={progressBarContainer}>
      <div style={{ ...progressBarFill, width: `${pct}%` }} />
    </div>
  )
}

function WelcomeWizard() {
  const [step, setStep] = useState<WizardStep>("welcome")
  const [serverUrl, setServerUrl] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [testResult, setTestResult] = useState<"idle" | "testing" | "success" | "failed">("idle")

  // --- Step: Welcome ---
  const renderWelcome = () => (
    <div style={stepContainer}>
      <div style={logoLarge}>NP</div>
      <h1 style={{ fontSize: "28px", fontWeight: "700", margin: "16px 0 8px", textAlign: "center" }}>
        Welcome to New Phone
      </h1>
      <p style={{ color: "#64748b", fontSize: "15px", textAlign: "center", maxWidth: "400px", margin: "0 auto 32px", lineHeight: "1.6" }}>
        Click-to-call any phone number on any webpage. Let's get you connected to your New Phone server.
      </p>
      <button onClick={() => setStep("server")} style={btnPrimary}>
        Get Started
      </button>
    </div>
  )

  // --- Step: Server URL ---
  const handleServerNext = useCallback(async () => {
    setError("")
    if (!serverUrl.trim()) {
      setError("Please enter your server URL")
      return
    }
    try {
      new URL(serverUrl)
    } catch {
      setError("Please enter a valid URL (e.g. https://phone.example.com)")
      return
    }

    // Save the URL
    await sendMessage({
      type: "SAVE_SETTINGS",
      payload: { apiBaseUrl: serverUrl.trim() } as Partial<ExtensionSettings>,
    })
    setStep("login")
  }, [serverUrl])

  const renderServer = () => (
    <div style={stepContainer}>
      <h2 style={stepTitle}>Server URL</h2>
      <p style={stepDesc}>Enter the URL of your New Phone server.</p>
      {error && <div style={errorBox}>{error}</div>}
      <label style={labelStyle}>
        Server URL
        <input
          type="url"
          value={serverUrl}
          onInput={(e) => setServerUrl((e.target as HTMLInputElement).value)}
          placeholder="https://phone.example.com"
          style={inputStyle}
          autofocus
          onKeyDown={(e) => e.key === "Enter" && handleServerNext()}
        />
      </label>
      <div style={btnRow}>
        <button onClick={() => setStep("welcome")} style={btnSecondary}>
          Back
        </button>
        <button onClick={handleServerNext} style={btnPrimary}>
          Next
        </button>
      </div>
    </div>
  )

  // --- Step: Login ---
  const handleLogin = useCallback(async (e: Event) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      const resp = await sendMessage({
        type: "AUTH_LOGIN",
        payload: {
          email,
          password,
          apiBaseUrl: serverUrl,
        } satisfies LoginPayload,
      })
      if (resp.success) {
        const state = resp.data as AuthState
        if (state.isAuthenticated) {
          setStep("test")
        } else if (state.mfaRequired) {
          // For onboarding, we skip MFA — user can complete in popup
          setError("MFA is required. Please complete sign-in via the extension popup after setup.")
          // Still move forward
          setTimeout(() => setStep("test"), 2000)
        } else {
          setError("Login failed. Please check your credentials.")
        }
      } else {
        setError(resp.error || "Login failed")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [email, password, serverUrl])

  const renderLogin = () => (
    <div style={stepContainer}>
      <h2 style={stepTitle}>Sign In</h2>
      <p style={stepDesc}>Sign in with your New Phone account.</p>
      {error && <div style={errorBox}>{error}</div>}
      <form onSubmit={handleLogin}>
        <label style={labelStyle}>
          Email
          <input
            type="email"
            value={email}
            onInput={(e) => setEmail((e.target as HTMLInputElement).value)}
            required
            style={inputStyle}
            autofocus
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
        <div style={btnRow}>
          <button type="button" onClick={() => setStep("server")} style={btnSecondary}>
            Back
          </button>
          <button type="submit" disabled={loading} style={btnPrimary}>
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </div>
      </form>
      <button
        type="button"
        onClick={() => setStep("test")}
        style={skipBtn}
      >
        Skip for now
      </button>
    </div>
  )

  // --- Step: Test Connection ---
  const handleTest = useCallback(async () => {
    setTestResult("testing")
    const ok = await apiHealthCheck(serverUrl)
    setTestResult(ok ? "success" : "failed")
  }, [serverUrl])

  const renderTest = () => (
    <div style={stepContainer}>
      <h2 style={stepTitle}>Test Connection</h2>
      <p style={stepDesc}>Verify the extension can communicate with your server.</p>
      <div style={{ textAlign: "center", margin: "24px 0" }}>
        {testResult === "idle" && (
          <button onClick={handleTest} style={btnPrimary}>
            Test Connection
          </button>
        )}
        {testResult === "testing" && (
          <div style={{ color: "#64748b" }}>
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              style={{ animation: "np-spin 0.8s linear infinite", marginBottom: "8px" }}
            >
              <circle cx="12" cy="12" r="10" stroke="#e2e8f0" stroke-width="3" />
              <path d="M22 12a10 10 0 00-10-10" stroke="#2563eb" stroke-width="3" stroke-linecap="round" />
            </svg>
            <div>Testing connection...</div>
            <style>{`@keyframes np-spin { to { transform: rotate(360deg); } }`}</style>
          </div>
        )}
        {testResult === "success" && (
          <div>
            <div style={{
              width: "48px",
              height: "48px",
              borderRadius: "50%",
              background: "#dcfce7",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: "12px",
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M5 13l4 4L19 7" stroke="#16a34a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </div>
            <div style={{ color: "#16a34a", fontWeight: "600", fontSize: "15px" }}>
              Connection successful
            </div>
          </div>
        )}
        {testResult === "failed" && (
          <div>
            <div style={{
              width: "48px",
              height: "48px",
              borderRadius: "50%",
              background: "#fef2f2",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: "12px",
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M6 18L18 6M6 6l12 12" stroke="#dc2626" stroke-width="2.5" stroke-linecap="round" />
              </svg>
            </div>
            <div style={{ color: "#dc2626", fontWeight: "600", fontSize: "15px", marginBottom: "8px" }}>
              Connection failed
            </div>
            <button onClick={handleTest} style={{ ...btnSecondary, fontSize: "13px" }}>
              Try Again
            </button>
          </div>
        )}
      </div>
      <div style={btnRow}>
        <button onClick={() => setStep("login")} style={btnSecondary}>
          Back
        </button>
        <button onClick={() => setStep("done")} style={btnPrimary}>
          {testResult === "success" ? "Finish" : "Skip"}
        </button>
      </div>
    </div>
  )

  // --- Step: Done ---
  const renderDone = () => (
    <div style={stepContainer}>
      <div style={{
        width: "64px",
        height: "64px",
        borderRadius: "50%",
        background: "#dbeafe",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        marginBottom: "16px",
      }}>
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <path d="M8 17l5 5L24 10" stroke="#2563eb" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </div>
      <h2 style={{ fontSize: "24px", fontWeight: "700", margin: "0 0 8px" }}>
        You're all set!
      </h2>
      <p style={{ color: "#64748b", fontSize: "14px", maxWidth: "380px", margin: "0 auto 8px", lineHeight: "1.6", textAlign: "center" }}>
        Phone numbers on web pages will now be clickable. You can also use the extension popup to dial numbers directly.
      </p>
      <div style={{ color: "#94a3b8", fontSize: "13px", marginBottom: "24px", textAlign: "center" }}>
        Access settings anytime from the extension icon in your toolbar.
      </div>
      <button
        onClick={() => window.close()}
        style={btnPrimary}
      >
        Close
      </button>
    </div>
  )

  const stepRenderers: Record<WizardStep, () => ReturnType<typeof renderWelcome>> = {
    welcome: renderWelcome,
    server: renderServer,
    login: renderLogin,
    test: renderTest,
    done: renderDone,
  }

  return (
    <div style={pageWrapper}>
      <div style={cardStyle}>
        <ProgressBar current={step} />
        {stepRenderers[step]()}
      </div>
    </div>
  )
}

// --- Styles ---

const pageWrapper: Record<string, string> = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  minHeight: "100vh",
  padding: "24px",
}

const cardStyle: Record<string, string> = {
  width: "100%",
  maxWidth: "480px",
  background: "#ffffff",
  border: "1px solid #e2e8f0",
  borderRadius: "12px",
  boxShadow: "0 4px 24px rgba(0,0,0,0.06)",
  overflow: "hidden",
}

const progressBarContainer: Record<string, string> = {
  height: "3px",
  background: "#e2e8f0",
  width: "100%",
}

const progressBarFill: Record<string, string> = {
  height: "100%",
  background: "#2563eb",
  transition: "width 0.3s ease",
  borderRadius: "0 2px 2px 0",
}

const stepContainer: Record<string, string> = {
  padding: "32px 32px 28px",
  textAlign: "center",
}

const stepTitle: Record<string, string> = {
  fontSize: "20px",
  fontWeight: "600",
  margin: "0 0 6px",
}

const stepDesc: Record<string, string> = {
  color: "#64748b",
  fontSize: "14px",
  margin: "0 0 20px",
}

const logoLarge: Record<string, string> = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: "56px",
  height: "56px",
  borderRadius: "14px",
  background: "#2563eb",
  color: "#ffffff",
  fontSize: "22px",
  fontWeight: "700",
}

const labelStyle: Record<string, string> = {
  display: "block",
  marginBottom: "12px",
  fontSize: "13px",
  fontWeight: "500",
  color: "#64748b",
  textAlign: "left",
}

const inputStyle: Record<string, string> = {
  display: "block",
  width: "100%",
  padding: "10px 12px",
  marginTop: "4px",
  border: "1px solid #e2e8f0",
  borderRadius: "6px",
  fontSize: "14px",
  outline: "none",
  boxSizing: "border-box",
}

const errorBox: Record<string, string> = {
  color: "#dc2626",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  borderRadius: "6px",
  padding: "8px 12px",
  fontSize: "13px",
  marginBottom: "12px",
  textAlign: "left",
}

const btnRow: Record<string, string> = {
  display: "flex",
  gap: "8px",
  justifyContent: "center",
  marginTop: "16px",
}

const btnPrimary: Record<string, string> = {
  padding: "10px 24px",
  background: "#2563eb",
  color: "#ffffff",
  border: "none",
  borderRadius: "6px",
  fontSize: "14px",
  fontWeight: "500",
  cursor: "pointer",
  fontFamily: "inherit",
}

const btnSecondary: Record<string, string> = {
  padding: "10px 20px",
  background: "#f1f5f9",
  color: "#334155",
  border: "1px solid #e2e8f0",
  borderRadius: "6px",
  fontSize: "14px",
  fontWeight: "500",
  cursor: "pointer",
  fontFamily: "inherit",
}

const skipBtn: Record<string, string> = {
  display: "block",
  margin: "12px auto 0",
  padding: "6px 12px",
  background: "transparent",
  color: "#94a3b8",
  border: "none",
  fontSize: "13px",
  cursor: "pointer",
  fontFamily: "inherit",
}

// --- Mount ---
render(<WelcomeWizard />, document.getElementById("app")!)
