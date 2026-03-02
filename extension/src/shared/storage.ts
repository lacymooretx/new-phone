import type { AuthState, ExtensionSettings, UserInfo } from "./types"

const DEFAULTS: ExtensionSettings = {
  callMethod: "originate",
  blockedSites: [],
  apiBaseUrl: "",
  numberDetectionEnabled: true,
  defaultCountryCode: "1",
}

export async function getSettings(): Promise<ExtensionSettings> {
  const result = await chrome.storage.local.get("settings")
  return { ...DEFAULTS, ...result.settings }
}

export async function saveSettings(settings: Partial<ExtensionSettings>): Promise<ExtensionSettings> {
  const current = await getSettings()
  const updated = { ...current, ...settings }
  await chrome.storage.local.set({ settings: updated })
  return updated
}

export async function getAuthTokens(): Promise<{ accessToken: string; refreshToken: string } | null> {
  const result = await chrome.storage.local.get("tokens")
  return result.tokens || null
}

export async function saveAuthTokens(accessToken: string, refreshToken: string): Promise<void> {
  await chrome.storage.local.set({ tokens: { accessToken, refreshToken } })
}

export async function clearAuthTokens(): Promise<void> {
  await chrome.storage.local.remove("tokens")
}

export async function getUserInfo(): Promise<UserInfo | null> {
  const result = await chrome.storage.local.get("userInfo")
  return result.userInfo || null
}

export async function saveUserInfo(info: UserInfo): Promise<void> {
  await chrome.storage.local.set({ userInfo: info })
}

export async function clearUserInfo(): Promise<void> {
  await chrome.storage.local.remove("userInfo")
}

export async function getAuthState(): Promise<AuthState> {
  const tokens = await getAuthTokens()
  const user = await getUserInfo()
  return {
    isAuthenticated: !!tokens?.accessToken,
    user: user || undefined,
  }
}

export async function clearAll(): Promise<void> {
  await clearAuthTokens()
  await clearUserInfo()
}
