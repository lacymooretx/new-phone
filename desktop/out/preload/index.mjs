import { contextBridge, ipcRenderer } from "electron";
contextBridge.exposeInMainWorld("electronAPI", {
  // --- Platform info ---
  platform: process.platform,
  // --- App info ---
  app: {
    getVersion: () => ipcRenderer.invoke("app:get-version"),
    getPlatform: () => ipcRenderer.invoke("app:get-platform")
  },
  // --- API configuration ---
  getApiBaseUrl: () => ipcRenderer.invoke("get-api-base-url"),
  getWsBaseUrl: () => ipcRenderer.invoke("get-ws-base-url"),
  // --- Notifications ---
  notifications: {
    showIncomingCall: (info) => ipcRenderer.invoke("notifications:show-incoming-call", info),
    show: (title, body, data) => ipcRenderer.invoke("notifications:show", title, body, data),
    onNotificationClick: (callback) => {
      const handler = (_event, data) => callback(data);
      ipcRenderer.on("notification-click", handler);
      return () => ipcRenderer.removeListener("notification-click", handler);
    }
  },
  // --- Legacy notification (kept for backward compat) ---
  showNotification: (title, body, data) => ipcRenderer.invoke("show-notification", title, body, data),
  setBadgeCount: (count) => ipcRenderer.invoke("set-badge-count", count),
  // --- Call actions (from global shortcuts) ---
  callActions: {
    onAnswer: (callback) => {
      const handler = (_event, action) => {
        if (action === "answer-call") callback();
      };
      ipcRenderer.on("shortcut", handler);
      return () => ipcRenderer.removeListener("shortcut", handler);
    },
    onHangup: (callback) => {
      const handler = (_event, action) => {
        if (action === "hangup") callback();
      };
      ipcRenderer.on("shortcut", handler);
      return () => ipcRenderer.removeListener("shortcut", handler);
    },
    onToggleMute: (callback) => {
      const handler = (_event, action) => {
        if (action === "toggle-mute") callback();
      };
      ipcRenderer.on("shortcut", handler);
      return () => ipcRenderer.removeListener("shortcut", handler);
    },
    onToggleSoftphone: (callback) => {
      const handler = (_event, action) => {
        if (action === "toggle-softphone") callback();
      };
      ipcRenderer.on("shortcut", handler);
      return () => ipcRenderer.removeListener("shortcut", handler);
    }
  },
  // --- Shortcut listener (generic, kept for backward compat) ---
  onShortcut: (callback) => {
    const handler = (_event, action) => callback(action);
    ipcRenderer.on("shortcut", handler);
    return () => ipcRenderer.removeListener("shortcut", handler);
  },
  // --- Audio devices ---
  audioDevices: {
    getPreferences: () => ipcRenderer.invoke("audio:get-preferences"),
    setPreferences: (prefs) => ipcRenderer.invoke("audio:set-preferences", prefs),
    resetPreferences: () => ipcRenderer.invoke("audio:reset-preferences")
  },
  // --- Deep link actions ---
  deepLink: {
    onAction: (callback) => {
      const handler = (_event, action) => callback(action);
      ipcRenderer.on("deep-link-action", handler);
      return () => ipcRenderer.removeListener("deep-link-action", handler);
    }
  },
  // --- Navigation (from tray/notifications) ---
  onNavigate: (callback) => {
    const handler = (_event, navPath) => callback(navPath);
    ipcRenderer.on("navigate", handler);
    return () => ipcRenderer.removeListener("navigate", handler);
  },
  // --- Auto-updater ---
  updater: {
    checkForUpdate: () => ipcRenderer.invoke("updater:check"),
    downloadUpdate: () => ipcRenderer.invoke("updater:download"),
    installUpdate: () => ipcRenderer.invoke("updater:install"),
    onUpdateAvailable: (callback) => {
      const handler = (_event, info) => callback(info);
      ipcRenderer.on("update-available", handler);
      return () => ipcRenderer.removeListener("update-available", handler);
    },
    onUpdateDownloading: (callback) => {
      const handler = () => callback();
      ipcRenderer.on("update-downloading", handler);
      return () => ipcRenderer.removeListener("update-downloading", handler);
    },
    onUpdateProgress: (callback) => {
      const handler = (_event, progress) => callback(progress);
      ipcRenderer.on("update-progress", handler);
      return () => ipcRenderer.removeListener("update-progress", handler);
    },
    onUpdateDownloaded: (callback) => {
      const handler = (_event, info) => callback(info);
      ipcRenderer.on("update-downloaded", handler);
      return () => ipcRenderer.removeListener("update-downloaded", handler);
    },
    onUpdateError: (callback) => {
      const handler = (_event, err) => callback(err);
      ipcRenderer.on("update-error", handler);
      return () => ipcRenderer.removeListener("update-error", handler);
    }
  }
});
