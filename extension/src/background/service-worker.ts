import { login, logout, checkAuth, completeMfa } from "@/shared/auth"
import { apiGet, apiPost, AuthError, NetworkError, TimeoutError } from "@/shared/api"
import { getSettings, saveSettings, getUserInfo } from "@/shared/storage"
import type {
  ExtMessage,
  LoginPayload,
  MfaPayload,
  InitiateCallPayload,
  MessageResponse,
  AuthState,
  ExtensionSettings,
  OriginateResponse,
  NumberHistoryEntry,
  ActiveCallInfo,
} from "@/shared/types"

// --- Badge colors ---
const BADGE_COLORS = {
  connected: "#22c55e", // green
  ringing: "#eab308",   // yellow
  error: "#dc2626",     // red
  offline: "#94a3b8",   // gray
} as const

// --- Track active call for badge ---
let lastCallState: string | null = null

function updateBadge(state: "connected" | "ringing" | "error" | "offline" | "clear") {
  if (state === "clear") {
    chrome.action.setBadgeText({ text: "" })
    lastCallState = null
    return
  }
  if (state === "connected" || state === "ringing") {
    chrome.action.setBadgeText({ text: "1" })
    chrome.action.setBadgeBackgroundColor({ color: BADGE_COLORS[state] })
    lastCallState = state
  } else {
    chrome.action.setBadgeText({ text: "" })
    chrome.action.setBadgeBackgroundColor({ color: BADGE_COLORS[state] })
    lastCallState = null
  }
}

// --- Extension install / update ---
chrome.runtime.onInstalled.addListener((details) => {
  // Create context menu
  chrome.contextMenus.create({
    id: "np-call-selection",
    title: 'Call "%s" with New Phone',
    contexts: ["selection"],
  })

  // Open onboarding on first install
  if (details.reason === "install") {
    const welcomeUrl = chrome.runtime.getURL("src/onboarding/welcome.html")
    chrome.tabs.create({ url: welcomeUrl })
  }
})

// --- Context menu click ---
chrome.contextMenus.onClicked.addListener(async (info) => {
  if (info.menuItemId === "np-call-selection" && info.selectionText) {
    const destination = info.selectionText.trim()
    await handleInitiateCall({ destination })
  }
})

// --- Periodic active call polling for badge ---
let badgePollInterval: ReturnType<typeof setInterval> | null = null

async function pollActiveCall() {
  try {
    const user = await getUserInfo()
    if (!user?.tenant_id) {
      updateBadge("clear")
      return
    }
    const data = await apiGet<ActiveCallInfo | null>(
      `/api/v1/tenants/${user.tenant_id}/calls/active`,
    )
    if (data && data.state !== "idle") {
      updateBadge(data.state === "ringing" ? "ringing" : "connected")
    } else {
      if (lastCallState) updateBadge("clear")
    }
  } catch (err) {
    if (err instanceof AuthError) {
      updateBadge("clear")
    }
    // Don't change badge on network errors — keep last known state
  }
}

function startBadgePolling() {
  if (badgePollInterval) return
  pollActiveCall()
  badgePollInterval = setInterval(pollActiveCall, 3000)
}

function stopBadgePolling() {
  if (badgePollInterval) {
    clearInterval(badgePollInterval)
    badgePollInterval = null
  }
  updateBadge("clear")
}

// Start polling when auth exists
checkAuth().then((state) => {
  if (state.isAuthenticated) {
    startBadgePolling()
  }
})

// --- Message router ---
chrome.runtime.onMessage.addListener(
  (message: ExtMessage, _sender, sendResponse) => {
    handleMessage(message)
      .then(sendResponse)
      .catch((err) => {
        const response: MessageResponse = {
          success: false,
          error: formatErrorMessage(err),
        }
        sendResponse(response)
      })
    return true // async response
  },
)

function formatErrorMessage(err: unknown): string {
  if (err instanceof AuthError) return "auth_expired:" + err.message
  if (err instanceof NetworkError) return "network:" + err.message
  if (err instanceof TimeoutError) return "timeout:" + err.message
  return String(err)
}

async function handleMessage(msg: ExtMessage): Promise<MessageResponse> {
  switch (msg.type) {
    case "AUTH_LOGIN": {
      const { email, password, apiBaseUrl } = msg.payload as LoginPayload
      const state = await login(email, password, apiBaseUrl)
      if (state.isAuthenticated) startBadgePolling()
      return { success: true, data: state }
    }
    case "AUTH_MFA_COMPLETE": {
      const { code } = msg.payload as MfaPayload
      const state = await completeMfa(code)
      if (state.isAuthenticated) startBadgePolling()
      return { success: true, data: state }
    }
    case "AUTH_LOGOUT":
      await logout()
      stopBadgePolling()
      return { success: true }
    case "AUTH_STATUS": {
      const state = await checkAuth()
      return { success: true, data: state }
    }
    case "INITIATE_CALL": {
      const payload = msg.payload as InitiateCallPayload
      return handleInitiateCall(payload)
    }
    case "LOOKUP_NUMBER": {
      const { number } = msg.payload as { number: string }
      const user = await getUserInfo()
      if (!user?.tenant_id)
        return { success: false, error: "Not authenticated" }
      const data = await apiGet(
        `/api/v1/tenants/${user.tenant_id}/extensions/lookup?number=${encodeURIComponent(number)}`,
      )
      return { success: true, data }
    }
    case "GET_RECENT_CALLS": {
      const { number } = (msg.payload as { number?: string }) || {}
      const user = await getUserInfo()
      if (!user?.tenant_id)
        return { success: false, error: "Not authenticated" }
      const params = number
        ? `?number=${encodeURIComponent(number)}&limit=10`
        : "?limit=10"
      const data = await apiGet<NumberHistoryEntry[]>(
        `/api/v1/tenants/${user.tenant_id}/calls/history${params}`,
      )
      return { success: true, data }
    }
    case "GET_ACTIVE_CALL": {
      const user = await getUserInfo()
      if (!user?.tenant_id)
        return { success: false, error: "Not authenticated" }
      try {
        const data = await apiGet<ActiveCallInfo | null>(
          `/api/v1/tenants/${user.tenant_id}/calls/active`,
        )
        return { success: true, data }
      } catch {
        return { success: true, data: null }
      }
    }
    case "OPEN_WEB_CLIENT": {
      const settings = await getSettings()
      const url = settings.apiBaseUrl
        .replace(/\/api.*$/, "")
        .replace(/\/$/, "")
      chrome.tabs.create({ url: `${url}/phone` })
      return { success: true }
    }
    case "GET_SETTINGS": {
      const settings = await getSettings()
      return { success: true, data: settings }
    }
    case "SAVE_SETTINGS": {
      const updated = await saveSettings(
        msg.payload as Partial<ExtensionSettings>,
      )
      return { success: true, data: updated }
    }
    case "TEST_CONNECTION": {
      const { apiBaseUrl } = msg.payload as { apiBaseUrl: string }
      try {
        const resp = await fetch(
          `${apiBaseUrl.replace(/\/$/, "")}/api/v1/health`,
        )
        return { success: resp.ok }
      } catch {
        return { success: false, error: "Unable to reach server" }
      }
    }
    default:
      return { success: false, error: `Unknown message type: ${msg.type}` }
  }
}

async function handleInitiateCall(
  payload: InitiateCallPayload,
): Promise<MessageResponse> {
  const settings = await getSettings()
  const method = payload.method || settings.callMethod

  if (method === "web_client") {
    const url = settings.apiBaseUrl
      .replace(/\/api.*$/, "")
      .replace(/\/$/, "")
    chrome.tabs.create({
      url: `${url}/phone?dial=${encodeURIComponent(payload.destination)}`,
    })
    return { success: true, data: { status: "opened_web_client" } }
  }

  // Default: originate via API (rings desk phone then bridges)
  const user = await getUserInfo()
  if (!user?.tenant_id)
    return { success: false, error: "Not authenticated" }
  const data = await apiPost<OriginateResponse>(
    `/api/v1/tenants/${user.tenant_id}/calls/originate`,
    { destination: payload.destination },
  )

  chrome.notifications.create({
    type: "basic",
    iconUrl: chrome.runtime.getURL("icons/icon128.png"),
    title: "Calling...",
    message: `Dialing ${payload.destination}`,
  })

  // Badge will update via polling
  return { success: true, data }
}
