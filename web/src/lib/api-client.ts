import { useAuthStore } from "@/stores/auth-store"
import { toast } from "sonner"
import { getApiBaseUrl } from "@/lib/desktop-bridge"

let apiBaseUrl = ""
let apiBaseUrlInitialized = false

async function ensureApiBaseUrl(): Promise<void> {
  if (!apiBaseUrlInitialized) {
    apiBaseUrl = await getApiBaseUrl()
    apiBaseUrlInitialized = true
  }
}

export class ApiError extends Error {
  status: number
  detail: string
  type?: string

  constructor(status: number, detail: string, type?: string) {
    super(detail)
    this.name = "ApiError"
    this.status = status
    this.detail = detail
    this.type = type
  }
}

async function refreshTokens(): Promise<boolean> {
  const { refreshToken, setTokens, logout } = useAuthStore.getState()
  if (!refreshToken) { toast.error("Your session has expired. Please log in again."); logout(); return false }

  try {
    await ensureApiBaseUrl()
    const res = await fetch(`${apiBaseUrl}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!res.ok) { toast.error("Your session has expired. Please log in again."); logout(); return false }
    const data = await res.json()
    setTokens(data.access_token, data.refresh_token)
    return true
  } catch {
    toast.error("Your session has expired. Please log in again.")
    logout()
    return false
  }
}

async function request<T>(method: string, path: string, options?: { body?: unknown; params?: Record<string, string> }): Promise<T> {
  await ensureApiBaseUrl()
  const { accessToken } = useAuthStore.getState()

  let url = path.startsWith("/") ? `${apiBaseUrl}${path}` : `${apiBaseUrl}/api/v1/${path}`
  if (options?.params) {
    const searchParams = new URLSearchParams(
      Object.entries(options.params).filter(([, v]) => v != null && v !== "")
    )
    if (searchParams.toString()) url += `?${searchParams}`
  }

  const headers: Record<string, string> = { "Content-Type": "application/json" }
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`

  let res = await fetch(url, {
    method,
    headers,
    body: options?.body ? JSON.stringify(options.body) : undefined,
  })

  // 401 → try refresh → retry once
  if (res.status === 401 && accessToken) {
    const refreshed = await refreshTokens()
    if (refreshed) {
      const { accessToken: newToken } = useAuthStore.getState()
      headers["Authorization"] = `Bearer ${newToken}`
      res = await fetch(url, { method, headers, body: options?.body ? JSON.stringify(options.body) : undefined })
    }
  }

  if (!res.ok) {
    let detail = res.statusText
    let type: string | undefined
    try {
      const err = await res.json()
      detail = err.detail || err.title || detail
      type = err.type
    } catch { /* ignore */ }

    // Provide user-friendly fallback messages for common status codes
    if (!detail || detail === res.statusText) {
      switch (res.status) {
        case 403: detail = "Access denied. You don't have permission for this action."; break
        case 404: detail = "The requested resource was not found."; break
        case 409: detail = "This operation conflicts with an existing resource."; break
        case 422: detail = "The submitted data is invalid. Please check your input."; break
        case 429: detail = "Too many requests. Please wait a moment and try again."; break
        default:
          if (res.status >= 500) detail = "A server error occurred. Please try again later."
      }
    }

    throw new ApiError(res.status, detail, type)
  }

  if (res.status === 204) return undefined as T
  return res.json()
}

export const apiClient = {
  get: <T>(path: string, params?: Record<string, string>) => request<T>("GET", path, { params }),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, { body }),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, { body }),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, { body }),
  delete: <T>(path: string) => request<T>("DELETE", path),
}
