import { globalShortcut, BrowserWindow, app } from "electron"

const SHORTCUTS: Record<string, string> = {
  "CmdOrCtrl+Shift+P": "toggle-softphone",
  "CmdOrCtrl+Shift+A": "answer-call",
  "CmdOrCtrl+Shift+H": "hangup",
  "CmdOrCtrl+Shift+M": "toggle-mute",
}

let registeredWindow: BrowserWindow | null = null

function doRegister(mainWindow: BrowserWindow): void {
  for (const [accelerator, action] of Object.entries(SHORTCUTS)) {
    globalShortcut.register(accelerator, () => {
      mainWindow.webContents.send("shortcut", action)
      // Bring window to focus for call-answer actions
      if (action === "answer-call") {
        mainWindow.show()
        mainWindow.focus()
      }
    })
  }
}

function doUnregister(): void {
  globalShortcut.unregisterAll()
}

/**
 * Register global keyboard shortcuts and set up focus/blur
 * registration so shortcuts only work when the app is focused
 * or when a call action is needed.
 */
export function registerGlobalShortcuts(mainWindow: BrowserWindow): void {
  registeredWindow = mainWindow

  // Register immediately
  doRegister(mainWindow)

  // On macOS the app stays alive when all windows close, so we
  // re-register when the app regains focus and unregister when it
  // loses focus. This prevents stealing shortcuts from other apps
  // when the user is not interacting with New Phone.
  //
  // On platforms where blur/focus is available on BrowserWindow:
  mainWindow.on("focus", () => {
    doRegister(mainWindow)
  })

  mainWindow.on("blur", () => {
    doUnregister()
  })

  // If the window is hidden (macOS hide-on-close), re-register on show
  mainWindow.on("show", () => {
    doRegister(mainWindow)
  })

  mainWindow.on("hide", () => {
    doUnregister()
  })
}

/**
 * Unregister all global shortcuts. Called on app will-quit.
 */
export function unregisterAllShortcuts(): void {
  doUnregister()
  registeredWindow = null
}
