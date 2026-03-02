import { Tray, Menu, nativeImage, BrowserWindow, app } from "electron"
import path from "node:path"

let tray: Tray | null = null

export function createTray(
  mainWindow: BrowserWindow,
  resourcesPath: string,
): Tray {
  const iconPath = path.join(resourcesPath, "icon.png")
  // Create a small 16x16 tray icon -- if file missing, use empty image
  let icon: Electron.NativeImage
  try {
    icon = nativeImage
      .createFromPath(iconPath)
      .resize({ width: 16, height: 16 })
  } catch {
    icon = nativeImage.createEmpty()
  }

  tray = new Tray(icon)
  tray.setToolTip("New Phone")

  buildTrayMenu(mainWindow)

  tray.on("click", () => {
    if (mainWindow.isVisible()) {
      mainWindow.hide()
    } else {
      mainWindow.show()
      mainWindow.focus()
    }
  })

  return tray
}

function buildTrayMenu(mainWindow: BrowserWindow): void {
  if (!tray) return

  const isVisible = mainWindow.isVisible()

  const contextMenu = Menu.buildFromTemplate([
    {
      label: isVisible ? "Hide Window" : "Show Window",
      click: () => {
        if (mainWindow.isVisible()) {
          mainWindow.hide()
        } else {
          mainWindow.show()
          mainWindow.focus()
        }
        // Rebuild menu so label updates
        buildTrayMenu(mainWindow)
      },
    },
    { type: "separator" },
    {
      label: "Status: Available",
      enabled: false,
    },
    {
      label: "Settings",
      click: () => {
        mainWindow.show()
        mainWindow.focus()
        mainWindow.webContents.send("navigate", "/settings")
      },
    },
    { type: "separator" },
    {
      label: "Quit",
      click: () => {
        app.isQuitting = true
        app.quit()
      },
    },
  ])

  tray.setContextMenu(contextMenu)
}

export function updateTrayTooltip(tooltip: string): void {
  if (tray) {
    tray.setToolTip(tooltip)
  }
}

/**
 * Update the status label in the tray menu.
 */
export function updateTrayStatus(
  status: string,
  mainWindow: BrowserWindow,
): void {
  if (!tray) return
  // Rebuild the menu with updated status
  const isVisible = mainWindow.isVisible()

  const contextMenu = Menu.buildFromTemplate([
    {
      label: isVisible ? "Hide Window" : "Show Window",
      click: () => {
        if (mainWindow.isVisible()) {
          mainWindow.hide()
        } else {
          mainWindow.show()
          mainWindow.focus()
        }
      },
    },
    { type: "separator" },
    {
      label: `Status: ${status}`,
      enabled: false,
    },
    {
      label: "Settings",
      click: () => {
        mainWindow.show()
        mainWindow.focus()
        mainWindow.webContents.send("navigate", "/settings")
      },
    },
    { type: "separator" },
    {
      label: "Quit",
      click: () => {
        app.isQuitting = true
        app.quit()
      },
    },
  ])

  tray.setContextMenu(contextMenu)
}
