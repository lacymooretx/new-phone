/**
 * Desktop Bridge — abstracts Electron-specific APIs.
 * When running in a browser, all functions gracefully return browser-appropriate defaults.
 */

/** Returns true when running inside Electron. */
export function isDesktop(): boolean {
  return !!window.electronAPI
}

let _apiBaseUrl: string | null = null

/**
 * Returns the API base URL.
 * - Electron: configured server URL (e.g. "http://localhost:8000")
 * - Browser: empty string (relative URLs)
 */
export async function getApiBaseUrl(): Promise<string> {
  if (_apiBaseUrl !== null) return _apiBaseUrl
  if (window.electronAPI) {
    _apiBaseUrl = await window.electronAPI.getApiBaseUrl()
  } else {
    _apiBaseUrl = ""
  }
  return _apiBaseUrl
}

let _wsBaseUrl: string | null = null

/**
 * Returns the WebSocket base URL.
 * - Electron: configured WS URL (e.g. "ws://localhost:8000")
 * - Browser: derived from window.location
 */
export async function getWsBaseUrl(): Promise<string> {
  if (_wsBaseUrl !== null) return _wsBaseUrl
  if (window.electronAPI) {
    _wsBaseUrl = await window.electronAPI.getWsBaseUrl()
  } else {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    _wsBaseUrl = `${protocol}//${window.location.host}`
  }
  return _wsBaseUrl
}

/** Show a native OS notification (Electron only). No-op in browser. */
export function showNativeNotification(title: string, body: string, data?: Record<string, unknown>): void {
  if (window.electronAPI) {
    window.electronAPI.showNotification(title, body, data)
  }
}

/** Set the dock/taskbar badge count (Electron only). No-op in browser. */
export function setBadgeCount(count: number): void {
  if (window.electronAPI) {
    window.electronAPI.setBadgeCount(count)
  }
}

/**
 * Subscribe to global keyboard shortcuts from Electron.
 * Returns an unsubscribe function. No-op in browser (returns no-op unsub).
 */
export function onShortcut(callback: (action: string) => void): () => void {
  if (window.electronAPI) {
    return window.electronAPI.onShortcut(callback)
  }
  return () => {}
}
