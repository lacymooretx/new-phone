import { app, BrowserWindow, ipcMain, Notification } from "electron"
import path from "node:path"
import { registerSchemePrivileges, registerProtocolHandler } from "./protocol"
import {
  registerDeepLinkProtocol,
  handleDeepLinkUrl,
} from "./deep-links"
import { loadWindowState, trackWindowState } from "./window-state"
import { createTray } from "./tray"
import { registerGlobalShortcuts, unregisterAllShortcuts } from "./shortcuts"
import { initAutoUpdater, registerUpdaterHandlers } from "./updater"
import { registerAudioHandlers } from "./audio"
import {
  registerNotificationHandlers,
  updateNotificationWindow,
} from "./notifications"

// Register custom protocol before app is ready
registerSchemePrivileges()

// Single instance lock
const gotTheLock = app.requestSingleInstanceLock()
if (!gotTheLock) {
  app.quit()
}

let mainWindow: BrowserWindow | null = null

// API server URL — configure via NP_API_URL env var or defaults to localhost
const API_BASE_URL = process.env.NP_API_URL || "http://localhost:8000"
const WS_BASE_URL =
  process.env.NP_WS_URL || API_BASE_URL.replace(/^http/, "ws")

function getWebBuildDir(): string {
  // In packaged app: resources/web (extraResources maps ../web/dist -> web)
  // In dev: ../web/dist
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "web")
  }
  return path.join(__dirname, "../../web/dist")
}

function createWindow(): void {
  const windowState = loadWindowState()

  mainWindow = new BrowserWindow({
    x: windowState.x,
    y: windowState.y,
    width: windowState.width,
    height: windowState.height,
    minWidth: 800,
    minHeight: 600,
    title: "New Phone",
    icon: path.join(
      app.isPackaged
        ? process.resourcesPath
        : path.join(__dirname, "../../resources"),
      "icon.png",
    ),
    webPreferences: {
      preload: path.join(__dirname, "../preload/index.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })

  if (windowState.isMaximized) {
    mainWindow.maximize()
  }

  trackWindowState(mainWindow)

  // Load the web app
  if (process.env.ELECTRON_DEV_URL) {
    // Dev mode: load from web dev server
    mainWindow.loadURL(process.env.ELECTRON_DEV_URL)
    mainWindow.webContents.openDevTools({ mode: "detach" })
  } else if (app.isPackaged) {
    // Production: load from custom protocol
    registerProtocolHandler(getWebBuildDir())
    mainWindow.loadURL("app://renderer/index.html")
  } else {
    // Dev build without dev server: load from web/dist
    registerProtocolHandler(getWebBuildDir())
    mainWindow.loadURL("app://renderer/index.html")
  }

  // Prevent window title from changing on navigation
  mainWindow.on("page-title-updated", (e) => e.preventDefault())

  // macOS: hide instead of close when clicking X
  mainWindow.on("close", (e) => {
    if (process.platform === "darwin" && !app.isQuitting) {
      e.preventDefault()
      mainWindow?.hide()
    }
  })
}

// Extend app to track quitting state on macOS
declare module "electron" {
  interface App {
    isQuitting?: boolean
  }
}

// --- IPC Handlers (core) ---
ipcMain.handle("app:get-version", () => app.getVersion())
ipcMain.handle("app:get-platform", () => process.platform)
ipcMain.handle("get-api-base-url", () => API_BASE_URL)
ipcMain.handle("get-ws-base-url", () => WS_BASE_URL)

ipcMain.handle(
  "show-notification",
  (
    _event,
    title: string,
    body: string,
    data?: Record<string, unknown>,
  ) => {
    const notification = new Notification({ title, body })
    notification.on("click", () => {
      mainWindow?.show()
      mainWindow?.focus()
      if (data?.path) {
        mainWindow?.webContents.send("navigate", data.path)
      }
    })
    notification.show()
  },
)

ipcMain.handle("set-badge-count", (_event, count: number) => {
  app.setBadgeCount(count)
})

// Audio device handlers (persisted preferences)
registerAudioHandlers()

// Updater IPC handlers (download/install triggers from renderer)
registerUpdaterHandlers()

// --- App Lifecycle ---
app.on("ready", () => {
  // Register newphone:// deep link protocol
  registerDeepLinkProtocol()

  createWindow()

  if (mainWindow) {
    createTray(
      mainWindow,
      app.isPackaged
        ? process.resourcesPath
        : path.join(__dirname, "../../resources"),
    )
    registerGlobalShortcuts(mainWindow)
    initAutoUpdater(mainWindow)
    registerNotificationHandlers(mainWindow)
  }
})

app.on("second-instance", (_event, argv) => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore()
    mainWindow.show()
    mainWindow.focus()
  }

  // On Windows/Linux the deep link URL is in argv
  const deepLinkUrl = argv.find((arg) => arg.startsWith("newphone://"))
  if (deepLinkUrl && mainWindow) {
    handleDeepLinkUrl(deepLinkUrl, mainWindow)
  }
})

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit()
  }
})

app.on("activate", () => {
  // macOS dock click: re-show window
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.show()
  } else {
    createWindow()
    if (mainWindow) {
      updateNotificationWindow(mainWindow)
    }
  }
})

app.on("before-quit", () => {
  app.isQuitting = true
})

app.on("will-quit", () => {
  unregisterAllShortcuts()
})

// macOS: handle deep link when app is already running
app.on("open-url", (event, url) => {
  event.preventDefault()
  if (mainWindow && !mainWindow.isDestroyed()) {
    handleDeepLinkUrl(url, mainWindow)
    mainWindow.show()
    mainWindow.focus()
  }
})
