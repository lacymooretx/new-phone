export interface ElectronAPI {
  platform: NodeJS.Platform
  getApiBaseUrl: () => Promise<string>
  getWsBaseUrl: () => Promise<string>
  showNotification: (title: string, body: string, data?: Record<string, unknown>) => Promise<void>
  setBadgeCount: (count: number) => Promise<void>
  onShortcut: (callback: (action: string) => void) => () => void
  onNavigate: (callback: (path: string) => void) => () => void
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
  }
}
