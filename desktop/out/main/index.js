import { protocol, net, app, nativeImage, Tray, Menu, globalShortcut, ipcMain, dialog, Notification, BrowserWindow } from "electron";
import path from "node:path";
import { pathToFileURL } from "node:url";
import fs from "node:fs";
import { autoUpdater } from "electron-updater";
import __cjs_mod__ from "node:module";
const __filename = import.meta.filename;
const __dirname = import.meta.dirname;
const require2 = __cjs_mod__.createRequire(import.meta.url);
const SCHEME = "app";
const MIME_TYPES = {
  ".html": "text/html",
  ".js": "application/javascript",
  ".mjs": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".eot": "application/vnd.ms-fontobject",
  ".webp": "image/webp",
  ".avif": "image/avif",
  ".mp3": "audio/mpeg",
  ".wav": "audio/wav",
  ".webm": "audio/webm"
};
function registerSchemePrivileges() {
  protocol.registerSchemesAsPrivileged([
    {
      scheme: SCHEME,
      privileges: {
        standard: true,
        secure: true,
        supportFetchAPI: true,
        corsEnabled: true,
        stream: true
      }
    }
  ]);
}
function registerProtocolHandler(webBuildDir) {
  protocol.handle(SCHEME, (request) => {
    const url = new URL(request.url);
    let pathname = decodeURIComponent(url.pathname);
    if (pathname.startsWith("/")) {
      pathname = pathname.slice(1);
    }
    let filePath = path.join(webBuildDir, pathname);
    const ext = path.extname(filePath);
    if (!ext) {
      filePath = path.join(webBuildDir, "index.html");
    }
    const fileUrl = pathToFileURL(filePath).href;
    const mimeType = MIME_TYPES[path.extname(filePath)] || "application/octet-stream";
    return net.fetch(fileUrl, {
      headers: { "Content-Type": mimeType }
    });
  });
}
const PROTOCOL = "newphone";
function registerDeepLinkProtocol() {
  if (process.defaultApp) {
    if (process.argv.length >= 2) {
      app.setAsDefaultProtocolClient(PROTOCOL, process.execPath, [
        process.argv[1]
      ]);
    }
  } else {
    app.setAsDefaultProtocolClient(PROTOCOL);
  }
}
function parseDeepLinkUrl(url) {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname || parsed.pathname.split("/")[0];
    const pathParts = parsed.pathname.split("/").filter((p) => p.length > 0);
    switch (host) {
      case "call": {
        const number = pathParts[0] || "";
        return { type: "call", value: number, raw: url };
      }
      case "extension": {
        const ext = pathParts[0] || "";
        return { type: "extension", value: ext, raw: url };
      }
      case "settings": {
        const section = pathParts[0] || "";
        return { type: "settings", value: section, raw: url };
      }
      default:
        return { type: "unknown", value: host, raw: url };
    }
  } catch {
    return { type: "unknown", value: "", raw: url };
  }
}
function handleDeepLinkUrl(url, mainWindow2) {
  const action = parseDeepLinkUrl(url);
  mainWindow2.webContents.send("deep-link-action", action);
}
const STATE_FILE = path.join(app.getPath("userData"), "window-state.json");
const DEFAULTS$1 = { x: 0, y: 0, width: 1280, height: 800, isMaximized: false };
let saveTimeout = null;
function loadWindowState() {
  try {
    const raw = fs.readFileSync(STATE_FILE, "utf-8");
    const state = JSON.parse(raw);
    if (typeof state.width === "number" && state.width > 200 && typeof state.height === "number" && state.height > 200) {
      return state;
    }
  } catch {
  }
  return DEFAULTS$1;
}
function saveWindowState(bounds) {
  try {
    fs.writeFileSync(STATE_FILE, JSON.stringify(bounds, null, 2));
  } catch {
  }
}
function trackWindowState(win) {
  const debouncedSave = () => {
    if (saveTimeout) clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
      if (win.isDestroyed()) return;
      const bounds = win.getBounds();
      saveWindowState({
        ...bounds,
        isMaximized: win.isMaximized()
      });
    }, 500);
  };
  win.on("resize", debouncedSave);
  win.on("move", debouncedSave);
  win.on("maximize", debouncedSave);
  win.on("unmaximize", debouncedSave);
}
let tray = null;
function createTray(mainWindow2, resourcesPath) {
  const iconPath = path.join(resourcesPath, "icon.png");
  let icon;
  try {
    icon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 });
  } catch {
    icon = nativeImage.createEmpty();
  }
  tray = new Tray(icon);
  tray.setToolTip("New Phone");
  buildTrayMenu(mainWindow2);
  tray.on("click", () => {
    if (mainWindow2.isVisible()) {
      mainWindow2.hide();
    } else {
      mainWindow2.show();
      mainWindow2.focus();
    }
  });
  return tray;
}
function buildTrayMenu(mainWindow2) {
  if (!tray) return;
  const isVisible = mainWindow2.isVisible();
  const contextMenu = Menu.buildFromTemplate([
    {
      label: isVisible ? "Hide Window" : "Show Window",
      click: () => {
        if (mainWindow2.isVisible()) {
          mainWindow2.hide();
        } else {
          mainWindow2.show();
          mainWindow2.focus();
        }
        buildTrayMenu(mainWindow2);
      }
    },
    { type: "separator" },
    {
      label: "Status: Available",
      enabled: false
    },
    {
      label: "Settings",
      click: () => {
        mainWindow2.show();
        mainWindow2.focus();
        mainWindow2.webContents.send("navigate", "/settings");
      }
    },
    { type: "separator" },
    {
      label: "Quit",
      click: () => {
        app.isQuitting = true;
        app.quit();
      }
    }
  ]);
  tray.setContextMenu(contextMenu);
}
const SHORTCUTS = {
  "CmdOrCtrl+Shift+P": "toggle-softphone",
  "CmdOrCtrl+Shift+A": "answer-call",
  "CmdOrCtrl+Shift+H": "hangup",
  "CmdOrCtrl+Shift+M": "toggle-mute"
};
function doRegister(mainWindow2) {
  for (const [accelerator, action] of Object.entries(SHORTCUTS)) {
    globalShortcut.register(accelerator, () => {
      mainWindow2.webContents.send("shortcut", action);
      if (action === "answer-call") {
        mainWindow2.show();
        mainWindow2.focus();
      }
    });
  }
}
function doUnregister() {
  globalShortcut.unregisterAll();
}
function registerGlobalShortcuts(mainWindow2) {
  doRegister(mainWindow2);
  mainWindow2.on("focus", () => {
    doRegister(mainWindow2);
  });
  mainWindow2.on("blur", () => {
    doUnregister();
  });
  mainWindow2.on("show", () => {
    doRegister(mainWindow2);
  });
  mainWindow2.on("hide", () => {
    doUnregister();
  });
}
function unregisterAllShortcuts() {
  doUnregister();
}
const CHECK_INTERVAL_MS = 4 * 60 * 60 * 1e3;
const INITIAL_DELAY_MS = 1e4;
function initAutoUpdater(mainWindow2) {
  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = true;
  autoUpdater.on("update-available", (info) => {
    mainWindow2.webContents.send("update-available", {
      version: info.version,
      releaseDate: info.releaseDate
    });
    dialog.showMessageBox(mainWindow2, {
      type: "info",
      title: "Update Available",
      message: `A new version (${info.version}) is available.`,
      detail: "Would you like to download it now?",
      buttons: ["Download", "Later"],
      defaultId: 0,
      cancelId: 1
    }).then((result) => {
      if (result.response === 0) {
        autoUpdater.downloadUpdate();
        mainWindow2.webContents.send("update-downloading");
      }
    });
  });
  autoUpdater.on("update-downloaded", (info) => {
    mainWindow2.webContents.send("update-downloaded", {
      version: info.version
    });
    dialog.showMessageBox(mainWindow2, {
      type: "info",
      title: "Update Ready",
      message: `Version ${info.version} has been downloaded.`,
      detail: "The application will restart to apply the update.",
      buttons: ["Restart Now", "Later"],
      defaultId: 0,
      cancelId: 1
    }).then((result) => {
      if (result.response === 0) {
        autoUpdater.quitAndInstall();
      }
    });
  });
  autoUpdater.on("download-progress", (progress) => {
    mainWindow2.webContents.send("update-progress", {
      percent: progress.percent,
      bytesPerSecond: progress.bytesPerSecond,
      transferred: progress.transferred,
      total: progress.total
    });
  });
  autoUpdater.on("error", (err) => {
    console.error("Auto-updater error:", err.message);
    mainWindow2.webContents.send("update-error", { message: err.message });
  });
  setTimeout(() => {
    autoUpdater.checkForUpdates().catch(() => {
    });
  }, INITIAL_DELAY_MS);
  setInterval(() => {
    autoUpdater.checkForUpdates().catch(() => {
    });
  }, CHECK_INTERVAL_MS);
}
function registerUpdaterHandlers() {
  ipcMain.handle("updater:check", async () => {
    try {
      const result = await autoUpdater.checkForUpdates();
      return {
        available: !!result?.updateInfo,
        version: result?.updateInfo?.version || null
      };
    } catch {
      return { available: false, version: null };
    }
  });
  ipcMain.handle("updater:download", () => {
    autoUpdater.downloadUpdate();
  });
  ipcMain.handle("updater:install", () => {
    autoUpdater.quitAndInstall();
  });
}
const AUDIO_PREFS_FILE = path.join(app.getPath("userData"), "audio-devices.json");
const DEFAULTS = {
  inputDeviceId: null,
  outputDeviceId: null,
  ringDeviceId: null
};
function loadAudioPreferences() {
  try {
    const raw = fs.readFileSync(AUDIO_PREFS_FILE, "utf-8");
    const prefs = JSON.parse(raw);
    return { ...DEFAULTS, ...prefs };
  } catch {
    return { ...DEFAULTS };
  }
}
function saveAudioPreferences(prefs) {
  try {
    fs.writeFileSync(AUDIO_PREFS_FILE, JSON.stringify(prefs, null, 2));
  } catch {
  }
}
function registerAudioHandlers() {
  ipcMain.handle("audio:get-preferences", () => {
    return loadAudioPreferences();
  });
  ipcMain.handle(
    "audio:set-preferences",
    (_event, prefs) => {
      const current = loadAudioPreferences();
      const updated = {
        inputDeviceId: prefs.inputDeviceId !== void 0 ? prefs.inputDeviceId : current.inputDeviceId,
        outputDeviceId: prefs.outputDeviceId !== void 0 ? prefs.outputDeviceId : current.outputDeviceId,
        ringDeviceId: prefs.ringDeviceId !== void 0 ? prefs.ringDeviceId : current.ringDeviceId
      };
      saveAudioPreferences(updated);
      return updated;
    }
  );
  ipcMain.handle("audio:reset-preferences", () => {
    saveAudioPreferences(DEFAULTS);
    return { ...DEFAULTS };
  });
}
let mainWindowRef = null;
function showIncomingCallNotification(info) {
  const title = "Incoming Call";
  const body = info.callerName ? `${info.callerName} (${info.callerNumber})` : info.callerNumber;
  const notification = new Notification({
    title,
    body,
    urgency: "critical",
    silent: false
    // Let the OS play the notification sound
  });
  notification.on("click", () => {
    if (mainWindowRef && !mainWindowRef.isDestroyed()) {
      mainWindowRef.show();
      mainWindowRef.focus();
      mainWindowRef.webContents.send("notification-click", {
        type: "incoming-call",
        callId: info.callId
      });
    }
  });
  notification.show();
}
function showGenericNotification(title, body, data) {
  const notification = new Notification({ title, body });
  notification.on("click", () => {
    if (mainWindowRef && !mainWindowRef.isDestroyed()) {
      mainWindowRef.show();
      mainWindowRef.focus();
      if (data) {
        mainWindowRef.webContents.send("notification-click", data);
      }
    }
  });
  notification.show();
}
function registerNotificationHandlers(mainWindow2) {
  mainWindowRef = mainWindow2;
  ipcMain.handle(
    "notifications:show-incoming-call",
    (_event, info) => {
      showIncomingCallNotification(info);
    }
  );
  ipcMain.handle(
    "notifications:show",
    (_event, title, body, data) => {
      showGenericNotification(title, body, data);
    }
  );
}
function updateNotificationWindow(mainWindow2) {
  mainWindowRef = mainWindow2;
}
registerSchemePrivileges();
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
}
let mainWindow = null;
const API_BASE_URL = process.env.NP_API_URL || "http://localhost:8000";
const WS_BASE_URL = process.env.NP_WS_URL || API_BASE_URL.replace(/^http/, "ws");
function getWebBuildDir() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "web");
  }
  return path.join(__dirname, "../../web/dist");
}
function createWindow() {
  const windowState = loadWindowState();
  mainWindow = new BrowserWindow({
    x: windowState.x,
    y: windowState.y,
    width: windowState.width,
    height: windowState.height,
    minWidth: 800,
    minHeight: 600,
    title: "New Phone",
    icon: path.join(
      app.isPackaged ? process.resourcesPath : path.join(__dirname, "../../resources"),
      "icon.png"
    ),
    webPreferences: {
      preload: path.join(__dirname, "../preload/index.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });
  if (windowState.isMaximized) {
    mainWindow.maximize();
  }
  trackWindowState(mainWindow);
  if (process.env.ELECTRON_DEV_URL) {
    mainWindow.loadURL(process.env.ELECTRON_DEV_URL);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else if (app.isPackaged) {
    registerProtocolHandler(getWebBuildDir());
    mainWindow.loadURL("app://renderer/index.html");
  } else {
    registerProtocolHandler(getWebBuildDir());
    mainWindow.loadURL("app://renderer/index.html");
  }
  mainWindow.on("page-title-updated", (e) => e.preventDefault());
  mainWindow.on("close", (e) => {
    if (process.platform === "darwin" && !app.isQuitting) {
      e.preventDefault();
      mainWindow?.hide();
    }
  });
}
ipcMain.handle("app:get-version", () => app.getVersion());
ipcMain.handle("app:get-platform", () => process.platform);
ipcMain.handle("get-api-base-url", () => API_BASE_URL);
ipcMain.handle("get-ws-base-url", () => WS_BASE_URL);
ipcMain.handle(
  "show-notification",
  (_event, title, body, data) => {
    const notification = new Notification({ title, body });
    notification.on("click", () => {
      mainWindow?.show();
      mainWindow?.focus();
      if (data?.path) {
        mainWindow?.webContents.send("navigate", data.path);
      }
    });
    notification.show();
  }
);
ipcMain.handle("set-badge-count", (_event, count) => {
  app.setBadgeCount(count);
});
registerAudioHandlers();
registerUpdaterHandlers();
app.on("ready", () => {
  registerDeepLinkProtocol();
  createWindow();
  if (mainWindow) {
    createTray(
      mainWindow,
      app.isPackaged ? process.resourcesPath : path.join(__dirname, "../../resources")
    );
    registerGlobalShortcuts(mainWindow);
    initAutoUpdater(mainWindow);
    registerNotificationHandlers(mainWindow);
  }
});
app.on("second-instance", (_event, argv) => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.focus();
  }
  const deepLinkUrl = argv.find((arg) => arg.startsWith("newphone://"));
  if (deepLinkUrl && mainWindow) {
    handleDeepLinkUrl(deepLinkUrl, mainWindow);
  }
});
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
app.on("activate", () => {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.show();
  } else {
    createWindow();
    if (mainWindow) {
      updateNotificationWindow(mainWindow);
    }
  }
});
app.on("before-quit", () => {
  app.isQuitting = true;
});
app.on("will-quit", () => {
  unregisterAllShortcuts();
});
app.on("open-url", (event, url) => {
  event.preventDefault();
  if (mainWindow && !mainWindow.isDestroyed()) {
    handleDeepLinkUrl(url, mainWindow);
    mainWindow.show();
    mainWindow.focus();
  }
});
