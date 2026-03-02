import { app, BrowserWindow } from "electron"
import fs from "node:fs"
import path from "node:path"

interface WindowBounds {
  x: number
  y: number
  width: number
  height: number
  isMaximized: boolean
}

const STATE_FILE = path.join(app.getPath("userData"), "window-state.json")
const DEFAULTS: WindowBounds = { x: 0, y: 0, width: 1280, height: 800, isMaximized: false }

let saveTimeout: ReturnType<typeof setTimeout> | null = null

export function loadWindowState(): WindowBounds {
  try {
    const raw = fs.readFileSync(STATE_FILE, "utf-8")
    const state = JSON.parse(raw) as WindowBounds
    // Basic validation
    if (typeof state.width === "number" && state.width > 200 && typeof state.height === "number" && state.height > 200) {
      return state
    }
  } catch {
    // File doesn't exist or is corrupt — use defaults
  }
  return DEFAULTS
}

function saveWindowState(bounds: WindowBounds): void {
  try {
    fs.writeFileSync(STATE_FILE, JSON.stringify(bounds, null, 2))
  } catch {
    // Ignore write errors
  }
}

export function trackWindowState(win: BrowserWindow): void {
  const debouncedSave = () => {
    if (saveTimeout) clearTimeout(saveTimeout)
    saveTimeout = setTimeout(() => {
      if (win.isDestroyed()) return
      const bounds = win.getBounds()
      saveWindowState({
        ...bounds,
        isMaximized: win.isMaximized(),
      })
    }, 500)
  }

  win.on("resize", debouncedSave)
  win.on("move", debouncedSave)
  win.on("maximize", debouncedSave)
  win.on("unmaximize", debouncedSave)
}
