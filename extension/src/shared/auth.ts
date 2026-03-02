import { apiLogin, apiMfaComplete } from "./api"
import {
  clearAll,
  getAuthState,
  saveAuthTokens,
  saveSettings,
  saveUserInfo,
  getSettings,
} from "./storage"
import type { AuthState, UserInfo } from "./types"

let mfaChallengeToken: string | null = null

export async function login(
  email: string,
  password: string,
  apiBaseUrl: string,
): Promise<AuthState> {
  // Persist the API base URL for subsequent requests
  await saveSettings({ apiBaseUrl })
  const result = await apiLogin(apiBaseUrl, email, password)

  if (result.mfa_required) {
    mfaChallengeToken = result.mfa_challenge_token || null
    return { isAuthenticated: false, mfaRequired: true }
  }

  if (result.access_token && result.refresh_token) {
    await saveAuthTokens(result.access_token, result.refresh_token)
    const user = decodeUserFromToken(result.access_token)
    if (user) await saveUserInfo(user)
    return { isAuthenticated: true, user: user || undefined }
  }

  return { isAuthenticated: false }
}

export async function completeMfa(code: string): Promise<AuthState> {
  if (!mfaChallengeToken) {
    return { isAuthenticated: false }
  }
  const settings = await getSettings()
  const result = await apiMfaComplete(settings.apiBaseUrl, mfaChallengeToken, code)
  mfaChallengeToken = null

  await saveAuthTokens(result.access_token, result.refresh_token)
  const user = decodeUserFromToken(result.access_token)
  if (user) await saveUserInfo(user)
  return { isAuthenticated: true, user: user || undefined }
}

export async function logout(): Promise<void> {
  mfaChallengeToken = null
  await clearAll()
}

export async function checkAuth(): Promise<AuthState> {
  return getAuthState()
}

function decodeUserFromToken(token: string): UserInfo | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]))
    return {
      id: payload.sub,
      email: payload.email || "",
      display_name: payload.display_name || payload.email || "",
      tenant_id: payload.tenant_id || "",
      role: payload.role || "",
      extension_number: payload.extension_number,
      extension_id: payload.extension_id,
    }
  } catch {
    return null
  }
}
