export interface AudioDevicePreference {
  inputDeviceId: string | null
  outputDeviceId: string | null
  ringDeviceId: string | null
}

export interface DeepLinkAction {
  type: string
  value: string
  raw: string
}

export interface UpdateInfo {
  version: string
  releaseDate: string
}

export interface UpdateProgress {
  percent: number
  bytesPerSecond: number
  transferred: number
  total: number
}

export interface IncomingCallInfo {
  callerName: string
  callerNumber: string
  callId: string
}

export interface ElectronAPI {
  // Platform
  platform: NodeJS.Platform

  // App info
  app: {
    getVersion: () => Promise<string>
    getPlatform: () => Promise<string>
  }

  // API configuration
  getApiBaseUrl: () => Promise<string>
  getWsBaseUrl: () => Promise<string>

  // Notifications
  notifications: {
    showIncomingCall: (info: IncomingCallInfo) => Promise<void>
    show: (
      title: string,
      body: string,
      data?: Record<string, unknown>,
    ) => Promise<void>
    onNotificationClick: (
      callback: (data: Record<string, unknown>) => void,
    ) => () => void
  }

  // Legacy notification API
  showNotification: (
    title: string,
    body: string,
    data?: Record<string, unknown>,
  ) => Promise<void>
  setBadgeCount: (count: number) => Promise<void>

  // Call actions (from global shortcuts)
  callActions: {
    onAnswer: (callback: () => void) => () => void
    onHangup: (callback: () => void) => () => void
    onToggleMute: (callback: () => void) => () => void
    onToggleSoftphone: (callback: () => void) => () => void
  }

  // Generic shortcut listener
  onShortcut: (callback: (action: string) => void) => () => void

  // Audio device management
  audioDevices: {
    getPreferences: () => Promise<AudioDevicePreference>
    setPreferences: (
      prefs: Partial<AudioDevicePreference>,
    ) => Promise<AudioDevicePreference>
    resetPreferences: () => Promise<AudioDevicePreference>
  }

  // Deep link handling
  deepLink: {
    onAction: (callback: (action: DeepLinkAction) => void) => () => void
  }

  // Navigation (from tray/notifications)
  onNavigate: (callback: (path: string) => void) => () => void

  // Auto-updater
  updater: {
    checkForUpdate: () => Promise<{
      available: boolean
      version: string | null
    }>
    downloadUpdate: () => Promise<void>
    installUpdate: () => Promise<void>
    onUpdateAvailable: (callback: (info: UpdateInfo) => void) => () => void
    onUpdateDownloading: (callback: () => void) => () => void
    onUpdateProgress: (callback: (progress: UpdateProgress) => void) => () => void
    onUpdateDownloaded: (
      callback: (info: { version: string }) => void,
    ) => () => void
    onUpdateError: (
      callback: (err: { message: string }) => void,
    ) => () => void
  }
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
  }
}
