import { protocol, net } from "electron"
import path from "node:path"
import { pathToFileURL } from "node:url"

const SCHEME = "app"

const MIME_TYPES: Record<string, string> = {
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
  ".webm": "audio/webm",
}

/**
 * Register the custom `app://` scheme as privileged before app is ready.
 * Must be called before app.whenReady().
 */
export function registerSchemePrivileges(): void {
  protocol.registerSchemesAsPrivileged([
    {
      scheme: SCHEME,
      privileges: {
        standard: true,
        secure: true,
        supportFetchAPI: true,
        corsEnabled: true,
        stream: true,
      },
    },
  ])
}

/**
 * Register the protocol handler for `app://` scheme.
 * Maps `app://renderer/path` to files in the web build directory.
 * Falls back to index.html for SPA routing (paths without file extensions).
 */
export function registerProtocolHandler(webBuildDir: string): void {
  protocol.handle(SCHEME, (request) => {
    const url = new URL(request.url)
    // Strip the "renderer" host part -- app://renderer/path -> /path
    let pathname = decodeURIComponent(url.pathname)

    // Remove leading slash for path.join
    if (pathname.startsWith("/")) {
      pathname = pathname.slice(1)
    }

    // Resolve the file path
    let filePath = path.join(webBuildDir, pathname)

    // Check if the path has a file extension
    const ext = path.extname(filePath)

    if (!ext) {
      // SPA fallback: no extension -> serve index.html
      filePath = path.join(webBuildDir, "index.html")
    }

    const fileUrl = pathToFileURL(filePath).href
    const mimeType =
      MIME_TYPES[path.extname(filePath)] || "application/octet-stream"

    return net.fetch(fileUrl, {
      headers: { "Content-Type": mimeType },
    })
  })
}
