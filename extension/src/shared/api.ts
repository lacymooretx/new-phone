import { getAuthTokens, getSettings, saveAuthTokens } from "./storage"

// --- Typed error classes ---

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = "ApiError"
  }
}

export class AuthError extends ApiError {
  constructor(message: string = "Authentication required") {
    super(401, message)
    this.name = "AuthError"
  }
}

export class NetworkError extends Error {
  constructor(message: string = "Network request failed") {
    super(message)
    this.name = "NetworkError"
  }
}

export class ServerError extends ApiError {
  constructor(status: number, message: string = "Server error") {
    super(status, message)
    this.name = "ServerError"
  }
}

export class TimeoutError extends Error {
  constructor(message: string = "Request timed out") {
    super(message)
    this.name = "TimeoutError"
  }
}

// --- Config ---

const REQUEST_TIMEOUT_MS = 10_000
const MAX_RETRIES = 3
const INITIAL_BACKOFF_MS = 500

// --- Helpers ---

async function getBaseUrl(): Promise<string> {
  const settings = await getSettings()
  return settings.apiBaseUrl.replace(/\/$/, "")
}

function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number = REQUEST_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  return fetch(url, { ...options, signal: controller.signal }).finally(() =>
    clearTimeout(timer),
  )
}

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function isRetryable(error: unknown): boolean {
  if (error instanceof NetworkError) return true
  if (error instanceof TimeoutError) return true
  if (error instanceof TypeError) return true // fetch network errors
  if (error instanceof DOMException && error.name === "AbortError") return true
  return false
}

async function withRetry<T>(
  fn: () => Promise<T>,
  maxRetries: number = MAX_RETRIES,
): Promise<T> {
  let lastError: unknown
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn()
    } catch (err) {
      lastError = err
      // Don't retry auth errors or client errors
      if (err instanceof AuthError) throw err
      if (err instanceof ApiError && err.status >= 400 && err.status < 500) throw err
      if (!isRetryable(err) && !(err instanceof ServerError)) throw err
      if (attempt < maxRetries) {
        const backoff = INITIAL_BACKOFF_MS * Math.pow(2, attempt)
        await sleep(backoff)
      }
    }
  }
  throw lastError
}

// --- Core fetch ---

async function fetchWithAuth(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const baseUrl = await getBaseUrl()
  const tokens = await getAuthTokens()

  const headers = new Headers(options.headers)
  if (tokens?.accessToken) {
    headers.set("Authorization", `Bearer ${tokens.accessToken}`)
  }
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json")
  }

  let response: Response
  try {
    response = await fetchWithTimeout(`${baseUrl}${path}`, { ...options, headers })
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new TimeoutError()
    }
    throw new NetworkError(err instanceof Error ? err.message : "Network request failed")
  }

  // Auto-refresh on 401
  if (response.status === 401 && tokens?.refreshToken) {
    const refreshed = await refreshAccessToken(tokens.refreshToken, baseUrl)
    if (refreshed) {
      headers.set("Authorization", `Bearer ${refreshed}`)
      try {
        response = await fetchWithTimeout(`${baseUrl}${path}`, { ...options, headers })
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          throw new TimeoutError()
        }
        throw new NetworkError(err instanceof Error ? err.message : "Network request failed")
      }
    } else {
      throw new AuthError("Session expired. Please sign in again.")
    }
  }

  return response
}

async function refreshAccessToken(
  refreshToken: string,
  baseUrl: string,
): Promise<string | null> {
  try {
    const resp = await fetchWithTimeout(
      `${baseUrl}/api/v1/auth/refresh`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      },
      REQUEST_TIMEOUT_MS,
    )
    if (!resp.ok) return null
    const data = await resp.json()
    await saveAuthTokens(data.access_token, data.refresh_token || refreshToken)
    return data.access_token
  } catch {
    return null
  }
}

function classifyError(status: number, body: string): ApiError {
  if (status === 401) return new AuthError(body || "Authentication required")
  if (status >= 500) return new ServerError(status, body || "Server error")
  return new ApiError(status, body || `Request failed with status ${status}`)
}

// --- Public API methods ---

export async function apiGet<T>(path: string): Promise<T> {
  return withRetry(async () => {
    const resp = await fetchWithAuth(path)
    if (!resp.ok) throw classifyError(resp.status, await resp.text())
    return resp.json()
  })
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return withRetry(async () => {
    const resp = await fetchWithAuth(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    })
    if (!resp.ok) throw classifyError(resp.status, await resp.text())
    return resp.json()
  })
}

export async function apiLogin(
  baseUrl: string,
  email: string,
  password: string,
): Promise<{
  access_token?: string
  refresh_token?: string
  mfa_required?: boolean
  mfa_challenge_token?: string
}> {
  let resp: Response
  try {
    resp = await fetchWithTimeout(
      `${baseUrl.replace(/\/$/, "")}/api/v1/auth/login`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      },
      REQUEST_TIMEOUT_MS,
    )
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new TimeoutError()
    }
    throw new NetworkError(err instanceof Error ? err.message : "Unable to reach server")
  }
  if (!resp.ok) throw classifyError(resp.status, await resp.text())
  return resp.json()
}

export async function apiMfaComplete(
  baseUrl: string,
  challengeToken: string,
  code: string,
): Promise<{ access_token: string; refresh_token: string }> {
  let resp: Response
  try {
    resp = await fetchWithTimeout(
      `${baseUrl.replace(/\/$/, "")}/api/v1/auth/mfa/verify`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ challenge_token: challengeToken, code }),
      },
      REQUEST_TIMEOUT_MS,
    )
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new TimeoutError()
    }
    throw new NetworkError(err instanceof Error ? err.message : "Unable to reach server")
  }
  if (!resp.ok) throw classifyError(resp.status, await resp.text())
  return resp.json()
}

/** Ping the API health endpoint. Returns true if reachable. */
export async function apiHealthCheck(baseUrl: string): Promise<boolean> {
  try {
    const resp = await fetchWithTimeout(
      `${baseUrl.replace(/\/$/, "")}/api/v1/health`,
      { method: "GET" },
      REQUEST_TIMEOUT_MS,
    )
    return resp.ok
  } catch {
    return false
  }
}
