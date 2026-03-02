import { autoUpdater } from "electron-updater"
import { BrowserWindow, dialog, ipcMain } from "electron"

const CHECK_INTERVAL_MS = 4 * 60 * 60 * 1000 // 4 hours
const INITIAL_DELAY_MS = 10_000 // 10 seconds after launch

/**
 * Initialize the auto-updater: check on launch (after a short delay)
 * and periodically every 4 hours. When an update is available, show
 * a native dialog asking the user to download. Once downloaded,
 * prompt to install and restart.
 */
export function initAutoUpdater(mainWindow: BrowserWindow): void {
  // Disable auto-download — let the user decide
  autoUpdater.autoDownload = false
  autoUpdater.autoInstallOnAppQuit = true

  autoUpdater.on("update-available", (info) => {
    // Notify renderer so the UI can show a badge/banner
    mainWindow.webContents.send("update-available", {
      version: info.version,
      releaseDate: info.releaseDate,
    })

    // Show native dialog
    dialog
      .showMessageBox(mainWindow, {
        type: "info",
        title: "Update Available",
        message: `A new version (${info.version}) is available.`,
        detail: "Would you like to download it now?",
        buttons: ["Download", "Later"],
        defaultId: 0,
        cancelId: 1,
      })
      .then((result) => {
        if (result.response === 0) {
          autoUpdater.downloadUpdate()
          mainWindow.webContents.send("update-downloading")
        }
      })
  })

  autoUpdater.on("update-downloaded", (info) => {
    mainWindow.webContents.send("update-downloaded", {
      version: info.version,
    })

    // Prompt to install and restart
    dialog
      .showMessageBox(mainWindow, {
        type: "info",
        title: "Update Ready",
        message: `Version ${info.version} has been downloaded.`,
        detail: "The application will restart to apply the update.",
        buttons: ["Restart Now", "Later"],
        defaultId: 0,
        cancelId: 1,
      })
      .then((result) => {
        if (result.response === 0) {
          autoUpdater.quitAndInstall()
        }
      })
  })

  autoUpdater.on("download-progress", (progress) => {
    mainWindow.webContents.send("update-progress", {
      percent: progress.percent,
      bytesPerSecond: progress.bytesPerSecond,
      transferred: progress.transferred,
      total: progress.total,
    })
  })

  autoUpdater.on("error", (err) => {
    // Log but don't bother the user — update server may not be configured yet
    console.error("Auto-updater error:", err.message)
    mainWindow.webContents.send("update-error", { message: err.message })
  })

  // Initial check after a short delay
  setTimeout(() => {
    autoUpdater.checkForUpdates().catch(() => {
      // Silently fail — update server likely not configured
    })
  }, INITIAL_DELAY_MS)

  // Periodic checks
  setInterval(() => {
    autoUpdater.checkForUpdates().catch(() => {
      // Silently fail
    })
  }, CHECK_INTERVAL_MS)
}

/**
 * Register IPC handlers so the renderer can trigger update actions.
 */
export function registerUpdaterHandlers(): void {
  ipcMain.handle("updater:check", async () => {
    try {
      const result = await autoUpdater.checkForUpdates()
      return {
        available: !!result?.updateInfo,
        version: result?.updateInfo?.version || null,
      }
    } catch {
      return { available: false, version: null }
    }
  })

  ipcMain.handle("updater:download", () => {
    autoUpdater.downloadUpdate()
  })

  ipcMain.handle("updater:install", () => {
    autoUpdater.quitAndInstall()
  })
}
