import { render } from "preact"
import { useState, useEffect, useCallback } from "preact/hooks"
import type { ExtMessage, MessageResponse, ExtensionSettings } from "@/shared/types"
import { apiHealthCheck } from "@/shared/api"

function sendMessage(msg: ExtMessage): Promise<MessageResponse> {
  return chrome.runtime.sendMessage(msg)
}

function OptionsPage() {
  const [settings, setSettings] = useState<ExtensionSettings | null>(null)
  const [saved, setSaved] = useState(false)
  const [blockedInput, setBlockedInput] = useState("")
  const [testStatus, setTestStatus] = useState<"idle" | "testing" | "success" | "failed">("idle")
  const [urlError, setUrlError] = useState("")

  useEffect(() => {
    sendMessage({ type: "GET_SETTINGS" }).then((resp) => {
      if (resp.success && resp.data) {
        const s = resp.data as ExtensionSettings
        setSettings(s)
        setBlockedInput(s.blockedSites.join("\n"))
      }
    })
  }, [])

  const validateUrl = useCallback((url: string): boolean => {
    setUrlError("")
    if (!url) return true // allow empty
    try {
      const parsed = new URL(url)
      if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
        setUrlError("URL must use https:// or http://")
        return false
      }
      return true
    } catch {
      setUrlError("Please enter a valid URL (e.g. https://phone.example.com)")
      return false
    }
  }, [])

  const handleTestConnection = useCallback(async () => {
    if (!settings?.apiBaseUrl) {
      setTestStatus("failed")
      return
    }
    if (!validateUrl(settings.apiBaseUrl)) {
      setTestStatus("failed")
      return
    }
    setTestStatus("testing")
    try {
      const ok = await apiHealthCheck(settings.apiBaseUrl)
      setTestStatus(ok ? "success" : "failed")
    } catch {
      setTestStatus("failed")
    }
    // Reset after 4 seconds
    setTimeout(() => setTestStatus("idle"), 4000)
  }, [settings?.apiBaseUrl, validateUrl])

  const handleSave = useCallback(async () => {
    if (!settings) return
    if (!validateUrl(settings.apiBaseUrl)) return

    const blockedSites = blockedInput
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean)

    const updated = { ...settings, blockedSites }
    const resp = await sendMessage({
      type: "SAVE_SETTINGS",
      payload: updated,
    })
    if (resp.success) {
      setSettings(resp.data as ExtensionSettings)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    }
  }, [settings, blockedInput, validateUrl])

  if (!settings) {
    return (
      <div style={{ padding: "32px", textAlign: "center", color: "#94a3b8" }}>
        Loading...
      </div>
    )
  }

  return (
    <div style={{ maxWidth: "560px", margin: "40px auto", padding: "0 24px" }}>
      <h1 style={{ fontSize: "22px", fontWeight: "600", marginBottom: "24px" }}>
        New Phone Settings
      </h1>

      {/* Server section */}
      <section style={sectionStyle}>
        <h2 style={sectionTitleStyle}>Server</h2>
        <label style={labelStyle}>
          API Base URL
          <input
            type="url"
            value={settings.apiBaseUrl}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value
              setSettings({ ...settings, apiBaseUrl: val })
              validateUrl(val)
            }}
            placeholder="https://phone.example.com"
            style={{
              ...inputStyle,
              borderColor: urlError ? "#dc2626" : "#e2e8f0",
            }}
          />
        </label>
        {urlError && (
          <div style={{ color: "#dc2626", fontSize: "12px", marginTop: "-6px", marginBottom: "8px" }}>
            {urlError}
          </div>
        )}
        <button onClick={handleTestConnection} disabled={testStatus === "testing"} style={testBtnStyle}>
          {testStatus === "testing" ? (
            <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <svg
                width="14"
                height="14"
                viewBox="0 0 14 14"
                fill="none"
                style={{ animation: "np-spin 0.8s linear infinite" }}
              >
                <circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-opacity="0.25" stroke-width="2" />
                <path d="M12.5 7a5.5 5.5 0 00-5.5-5.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              </svg>
              Testing...
            </span>
          ) : testStatus === "success" ? (
            <span style={{ color: "#16a34a" }}>Connected successfully</span>
          ) : testStatus === "failed" ? (
            <span style={{ color: "#dc2626" }}>Connection failed</span>
          ) : (
            "Test Connection"
          )}
        </button>
        <style>{`@keyframes np-spin { to { transform: rotate(360deg); } }`}</style>
      </section>

      {/* Call Method section */}
      <section style={sectionStyle}>
        <h2 style={sectionTitleStyle}>Call Method</h2>
        <label
          style={{
            ...labelStyle,
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <input
            type="radio"
            name="callMethod"
            value="originate"
            checked={settings.callMethod === "originate"}
            onChange={() =>
              setSettings({ ...settings, callMethod: "originate" })
            }
          />
          <div>
            <div style={{ fontWeight: "500" }}>Desk Phone (Originate)</div>
            <div style={{ fontSize: "12px", color: "#64748b" }}>
              Rings your desk phone first, then bridges to the destination
            </div>
          </div>
        </label>
        <label
          style={{
            ...labelStyle,
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <input
            type="radio"
            name="callMethod"
            value="web_client"
            checked={settings.callMethod === "web_client"}
            onChange={() =>
              setSettings({ ...settings, callMethod: "web_client" })
            }
          />
          <div>
            <div style={{ fontWeight: "500" }}>Web Client</div>
            <div style={{ fontSize: "12px", color: "#64748b" }}>
              Opens the web softphone with the number pre-dialed
            </div>
          </div>
        </label>
      </section>

      {/* Number Detection section */}
      <section style={sectionStyle}>
        <h2 style={sectionTitleStyle}>Number Detection</h2>
        <label
          style={{
            ...labelStyle,
            display: "flex",
            alignItems: "center",
            gap: "8px",
            marginBottom: "12px",
          }}
        >
          <input
            type="checkbox"
            checked={settings.numberDetectionEnabled}
            onChange={(e) =>
              setSettings({
                ...settings,
                numberDetectionEnabled: (e.target as HTMLInputElement).checked,
              })
            }
          />
          <div>
            <div style={{ fontWeight: "500" }}>Detect phone numbers on pages</div>
            <div style={{ fontSize: "12px", color: "#64748b" }}>
              Automatically find and make phone numbers clickable
            </div>
          </div>
        </label>

        <label style={labelStyle}>
          Default Country Code
          <div style={{ display: "flex", alignItems: "center", gap: "4px", marginTop: "4px" }}>
            <span style={{ fontSize: "14px", color: "#64748b" }}>+</span>
            <input
              type="text"
              value={settings.defaultCountryCode}
              onInput={(e) =>
                setSettings({
                  ...settings,
                  defaultCountryCode: (e.target as HTMLInputElement).value.replace(/\D/g, ""),
                })
              }
              placeholder="1"
              maxLength={3}
              style={{ ...inputStyle, width: "60px" }}
            />
            <span style={{ fontSize: "12px", color: "#94a3b8" }}>
              Used when country code is not present
            </span>
          </div>
        </label>
      </section>

      {/* Blocked Sites section */}
      <section style={sectionStyle}>
        <h2 style={sectionTitleStyle}>Blocked Sites</h2>
        <p
          style={{
            fontSize: "12px",
            color: "#64748b",
            margin: "0 0 8px",
          }}
        >
          Phone number detection will be disabled on these domains. One per
          line.
        </p>
        <textarea
          value={blockedInput}
          onInput={(e) =>
            setBlockedInput((e.target as HTMLTextAreaElement).value)
          }
          placeholder={"example.com\nbank.example.org"}
          rows={5}
          style={{ ...inputStyle, resize: "vertical" }}
        />
      </section>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          marginTop: "16px",
        }}
      >
        <button onClick={handleSave} style={btnPrimaryStyle}>
          Save Settings
        </button>
        {saved && (
          <span
            style={{
              color: "#16a34a",
              fontSize: "13px",
              fontWeight: "500",
            }}
          >
            Settings saved
          </span>
        )}
      </div>
    </div>
  )
}

// --- Styles ---
const sectionStyle: Record<string, string> = {
  marginBottom: "24px",
  padding: "16px",
  background: "#ffffff",
  border: "1px solid #e2e8f0",
  borderRadius: "8px",
}

const sectionTitleStyle: Record<string, string> = {
  fontSize: "15px",
  fontWeight: "600",
  margin: "0 0 12px",
}

const labelStyle: Record<string, string> = {
  display: "block",
  marginBottom: "10px",
  fontSize: "13px",
  fontWeight: "500",
  color: "#334155",
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

const testBtnStyle: Record<string, string> = {
  padding: "8px 14px",
  background: "#f1f5f9",
  color: "#334155",
  border: "1px solid #e2e8f0",
  borderRadius: "6px",
  fontSize: "13px",
  fontWeight: "500",
  cursor: "pointer",
  fontFamily: "inherit",
}

const btnPrimaryStyle: Record<string, string> = {
  padding: "10px 20px",
  background: "#2563eb",
  color: "#ffffff",
  border: "none",
  borderRadius: "6px",
  fontSize: "14px",
  fontWeight: "500",
  cursor: "pointer",
}

// --- Mount ---
render(<OptionsPage />, document.getElementById("app")!)
