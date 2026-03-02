import { app, ipcMain } from "electron"
import fs from "node:fs"
import path from "node:path"

export interface AudioDevicePreference {
  inputDeviceId: string | null
  outputDeviceId: string | null
  ringDeviceId: string | null
}

const AUDIO_PREFS_FILE = path.join(app.getPath("userData"), "audio-devices.json")

const DEFAULTS: AudioDevicePreference = {
  inputDeviceId: null,
  outputDeviceId: null,
  ringDeviceId: null,
}

function loadAudioPreferences(): AudioDevicePreference {
  try {
    const raw = fs.readFileSync(AUDIO_PREFS_FILE, "utf-8")
    const prefs = JSON.parse(raw) as AudioDevicePreference
    return { ...DEFAULTS, ...prefs }
  } catch {
    return { ...DEFAULTS }
  }
}

function saveAudioPreferences(prefs: AudioDevicePreference): void {
  try {
    fs.writeFileSync(AUDIO_PREFS_FILE, JSON.stringify(prefs, null, 2))
  } catch {
    // Ignore write errors — userData dir may not exist yet on first run
  }
}

/**
 * Register IPC handlers for audio device management.
 *
 * The renderer sends the available device list (from navigator.mediaDevices)
 * and the main process persists the user's selection to disk.
 */
export function registerAudioHandlers(): void {
  ipcMain.handle("audio:get-preferences", () => {
    return loadAudioPreferences()
  })

  ipcMain.handle(
    "audio:set-preferences",
    (_event, prefs: Partial<AudioDevicePreference>) => {
      const current = loadAudioPreferences()
      const updated: AudioDevicePreference = {
        inputDeviceId:
          prefs.inputDeviceId !== undefined
            ? prefs.inputDeviceId
            : current.inputDeviceId,
        outputDeviceId:
          prefs.outputDeviceId !== undefined
            ? prefs.outputDeviceId
            : current.outputDeviceId,
        ringDeviceId:
          prefs.ringDeviceId !== undefined
            ? prefs.ringDeviceId
            : current.ringDeviceId,
      }
      saveAudioPreferences(updated)
      return updated
    },
  )

  ipcMain.handle("audio:reset-preferences", () => {
    saveAudioPreferences(DEFAULTS)
    return { ...DEFAULTS }
  })
}
