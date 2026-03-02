import { contextBridge, ipcRenderer } from "electron"

contextBridge.exposeInMainWorld("electronAPI", {
  // --- Platform info ---
  platform: process.platform,

  // --- App info ---
  app: {
    getVersion: (): Promise<string> => ipcRenderer.invoke("app:get-version"),
    getPlatform: (): Promise<string> => ipcRenderer.invoke("app:get-platform"),
  },

  // --- API configuration ---
  getApiBaseUrl: (): Promise<string> =>
    ipcRenderer.invoke("get-api-base-url"),

  getWsBaseUrl: (): Promise<string> =>
    ipcRenderer.invoke("get-ws-base-url"),

  // --- Notifications ---
  notifications: {
    showIncomingCall: (info: {
      callerName: string
      callerNumber: string
      callId: string
    }): Promise<void> =>
      ipcRenderer.invoke("notifications:show-incoming-call", info),

    show: (
      title: string,
      body: string,
      data?: Record<string, unknown>,
    ): Promise<void> =>
      ipcRenderer.invoke("notifications:show", title, body, data),

    onNotificationClick: (
      callback: (data: Record<string, unknown>) => void,
    ): (() => void) => {
      const handler = (
        _event: Electron.IpcRendererEvent,
        data: Record<string, unknown>,
      ) => callback(data)
      ipcRenderer.on("notification-click", handler)
      return () => ipcRenderer.removeListener("notification-click", handler)
    },
  },

  // --- Legacy notification (kept for backward compat) ---
  showNotification: (
    title: string,
    body: string,
    data?: Record<string, unknown>,
  ): Promise<void> =>
    ipcRenderer.invoke("show-notification", title, body, data),

  setBadgeCount: (count: number): Promise<void> =>
    ipcRenderer.invoke("set-badge-count", count),

  // --- Call actions (from global shortcuts) ---
  callActions: {
    onAnswer: (callback: () => void): (() => void) => {
      const handler = (
        _event: Electron.IpcRendererEvent,
        action: string,
      ) => {
        if (action === "answer-call") callback()
      }
      ipcRenderer.on("shortcut", handler)
      return () => ipcRenderer.removeListener("shortcut", handler)
    },

    onHangup: (callback: () => void): (() => void) => {
      const handler = (
        _event: Electron.IpcRendererEvent,
        action: string,
      ) => {
        if (action === "hangup") callback()
      }
      ipcRenderer.on("shortcut", handler)
      return () => ipcRenderer.removeListener("shortcut", handler)
    },

    onToggleMute: (callback: () => void): (() => void) => {
      const handler = (
        _event: Electron.IpcRendererEvent,
        action: string,
      ) => {
        if (action === "toggle-mute") callback()
      }
      ipcRenderer.on("shortcut", handler)
      return () => ipcRenderer.removeListener("shortcut", handler)
    },

    onToggleSoftphone: (callback: () => void): (() => void) => {
      const handler = (
        _event: Electron.IpcRendererEvent,
        action: string,
      ) => {
        if (action === "toggle-softphone") callback()
      }
      ipcRenderer.on("shortcut", handler)
      return () => ipcRenderer.removeListener("shortcut", handler)
    },
  },

  // --- Shortcut listener (generic, kept for backward compat) ---
  onShortcut: (callback: (action: string) => void): (() => void) => {
    const handler = (
      _event: Electron.IpcRendererEvent,
      action: string,
    ) => callback(action)
    ipcRenderer.on("shortcut", handler)
    return () => ipcRenderer.removeListener("shortcut", handler)
  },

  // --- Audio devices ---
  audioDevices: {
    getPreferences: (): Promise<{
      inputDeviceId: string | null
      outputDeviceId: string | null
      ringDeviceId: string | null
    }> => ipcRenderer.invoke("audio:get-preferences"),

    setPreferences: (prefs: {
      inputDeviceId?: string | null
      outputDeviceId?: string | null
      ringDeviceId?: string | null
    }): Promise<{
      inputDeviceId: string | null
      outputDeviceId: string | null
      ringDeviceId: string | null
    }> => ipcRenderer.invoke("audio:set-preferences", prefs),

    resetPreferences: (): Promise<{
      inputDeviceId: string | null
      outputDeviceId: string | null
      ringDeviceId: string | null
    }> => ipcRenderer.invoke("audio:reset-preferences"),
  },

  // --- Deep link actions ---
  deepLink: {
    onAction: (
      callback: (action: {
        type: string
        value: string
        raw: string
      }) => void,
    ): (() => void) => {
      const handler = (
        _event: Electron.IpcRendererEvent,
        action: { type: string; value: string; raw: string },
      ) => callback(action)
      ipcRenderer.on("deep-link-action", handler)
      return () => ipcRenderer.removeListener("deep-link-action", handler)
    },
  },

  // --- Navigation (from tray/notifications) ---
  onNavigate: (callback: (path: string) => void): (() => void) => {
    const handler = (
      _event: Electron.IpcRendererEvent,
      navPath: string,
    ) => callback(navPath)
    ipcRenderer.on("navigate", handler)
    return () => ipcRenderer.removeListener("navigate", handler)
  },

  // --- Auto-updater ---
  updater: {
    checkForUpdate: (): Promise<{
      available: boolean
      version: string | null
    }> => ipcRenderer.invoke("updater:check"),

    downloadUpdate: (): Promise<void> =>
      ipcRenderer.invoke("updater:download"),

    installUpdate: (): Promise<void> =>
      ipcRenderer.invoke("updater:install"),

    onUpdateAvailable: (
      callback: (info: { version: string; releaseDate: string }) => void,
    ): (() => void) => {
      const handler = (
        _event: Electron.IpcRendererEvent,
        info: { version: string; releaseDate: string },
      ) => callback(info)
      ipcRenderer.on("update-available", handler)
      return () => ipcRenderer.removeListener("update-available", handler)
    },

    onUpdateDownloading: (callback: () => void): (() => void) => {
      const handler = () => callback()
      ipcRenderer.on("update-downloading", handler)
      return () => ipcRenderer.removeListener("update-downloading", handler)
    },

    onUpdateProgress: (
      callback: (progress: {
        percent: number
        bytesPerSecond: number
        transferred: number
        total: number
      }) => void,
    ): (() => void) => {
      const handler = (
        _event: Electron.IpcRendererEvent,
        progress: {
          percent: number
          bytesPerSecond: number
          transferred: number
          total: number
        },
      ) => callback(progress)
      ipcRenderer.on("update-progress", handler)
      return () => ipcRenderer.removeListener("update-progress", handler)
    },

    onUpdateDownloaded: (
      callback: (info: { version: string }) => void,
    ): (() => void) => {
      const handler = (
        _event: Electron.IpcRendererEvent,
        info: { version: string },
      ) => callback(info)
      ipcRenderer.on("update-downloaded", handler)
      return () => ipcRenderer.removeListener("update-downloaded", handler)
    },

    onUpdateError: (
      callback: (err: { message: string }) => void,
    ): (() => void) => {
      const handler = (
        _event: Electron.IpcRendererEvent,
        err: { message: string },
      ) => callback(err)
      ipcRenderer.on("update-error", handler)
      return () => ipcRenderer.removeListener("update-error", handler)
    },
  },
})
