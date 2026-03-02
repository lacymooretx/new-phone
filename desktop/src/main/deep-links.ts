import { app, BrowserWindow } from "electron"

const PROTOCOL = "newphone"

export interface DeepLinkAction {
  type: "call" | "extension" | "settings" | "unknown"
  value: string
  raw: string
}

/**
 * Register `newphone://` as the default protocol client.
 * On macOS this is handled via Info.plist + open-url event.
 * On Windows/Linux this registers the app to handle the protocol.
 */
export function registerDeepLinkProtocol(): void {
  if (process.defaultApp) {
    // In development, register with the path to electron + script
    if (process.argv.length >= 2) {
      app.setAsDefaultProtocolClient(PROTOCOL, process.execPath, [
        process.argv[1],
      ])
    }
  } else {
    app.setAsDefaultProtocolClient(PROTOCOL)
  }
}

/**
 * Parse a newphone:// URL into a structured action.
 *
 * Supported URL formats:
 *   newphone://call/+15551234567
 *   newphone://call/15551234567
 *   newphone://extension/100
 *   newphone://settings
 *   newphone://settings/audio
 */
export function parseDeepLinkUrl(url: string): DeepLinkAction {
  try {
    // URL constructor handles newphone://call/+15551234567
    const parsed = new URL(url)
    const host = parsed.hostname || parsed.pathname.split("/")[0]
    // pathname might be "//call/+15551234567" or "/+15551234567"
    const pathParts = parsed.pathname
      .split("/")
      .filter((p) => p.length > 0)

    switch (host) {
      case "call": {
        // newphone://call/+15551234567
        const number = pathParts[0] || ""
        return { type: "call", value: number, raw: url }
      }
      case "extension": {
        // newphone://extension/100
        const ext = pathParts[0] || ""
        return { type: "extension", value: ext, raw: url }
      }
      case "settings": {
        // newphone://settings or newphone://settings/audio
        const section = pathParts[0] || ""
        return { type: "settings", value: section, raw: url }
      }
      default:
        return { type: "unknown", value: host, raw: url }
    }
  } catch {
    return { type: "unknown", value: "", raw: url }
  }
}

/**
 * Handle an incoming deep link URL by parsing it and sending
 * the action to the renderer process.
 */
export function handleDeepLinkUrl(
  url: string,
  mainWindow: BrowserWindow,
): void {
  const action = parseDeepLinkUrl(url)
  mainWindow.webContents.send("deep-link-action", action)
}
