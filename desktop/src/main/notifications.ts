import { Notification, BrowserWindow, ipcMain } from "electron"

let mainWindowRef: BrowserWindow | null = null

export interface IncomingCallInfo {
  callerName: string
  callerNumber: string
  callId: string
}

/**
 * Show a native OS notification for an incoming call.
 * Clicking the notification brings the main window to focus
 * and tells the renderer to navigate to the active call.
 */
function showIncomingCallNotification(info: IncomingCallInfo): void {
  const title = "Incoming Call"
  const body = info.callerName
    ? `${info.callerName} (${info.callerNumber})`
    : info.callerNumber

  const notification = new Notification({
    title,
    body,
    urgency: "critical",
    silent: false, // Let the OS play the notification sound
  })

  notification.on("click", () => {
    if (mainWindowRef && !mainWindowRef.isDestroyed()) {
      mainWindowRef.show()
      mainWindowRef.focus()
      mainWindowRef.webContents.send("notification-click", {
        type: "incoming-call",
        callId: info.callId,
      })
    }
  })

  notification.show()
}

/**
 * Show a generic notification (voicemail, missed call, SMS, etc.)
 */
function showGenericNotification(
  title: string,
  body: string,
  data?: Record<string, unknown>,
): void {
  const notification = new Notification({ title, body })

  notification.on("click", () => {
    if (mainWindowRef && !mainWindowRef.isDestroyed()) {
      mainWindowRef.show()
      mainWindowRef.focus()
      if (data) {
        mainWindowRef.webContents.send("notification-click", data)
      }
    }
  })

  notification.show()
}

/**
 * Register IPC handlers for notification management and
 * store a reference to the main window for click handling.
 */
export function registerNotificationHandlers(mainWindow: BrowserWindow): void {
  mainWindowRef = mainWindow

  ipcMain.handle(
    "notifications:show-incoming-call",
    (_event, info: IncomingCallInfo) => {
      showIncomingCallNotification(info)
    },
  )

  ipcMain.handle(
    "notifications:show",
    (
      _event,
      title: string,
      body: string,
      data?: Record<string, unknown>,
    ) => {
      showGenericNotification(title, body, data)
    },
  )
}

/**
 * Update the stored main window reference (e.g. if window is recreated).
 */
export function updateNotificationWindow(mainWindow: BrowserWindow): void {
  mainWindowRef = mainWindow
}
