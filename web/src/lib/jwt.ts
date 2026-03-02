export interface JwtPayload {
  sub: string       // user_id UUID
  tenant_id: string // UUID
  role: "msp_super_admin" | "msp_tech" | "tenant_admin" | "tenant_manager" | "tenant_user"
  type: "access" | "refresh"
  language?: string
  exp: number
  iat: number
}

export function decodeJwtPayload(token: string): JwtPayload {
  const parts = token.split(".")
  if (parts.length !== 3) throw new Error("Invalid JWT")
  const payload = parts[1]
  const decoded = atob(payload.replace(/-/g, "+").replace(/_/g, "/"))
  return JSON.parse(decoded)
}

export function isTokenExpired(token: string, bufferSeconds = 30): boolean {
  try {
    const payload = decodeJwtPayload(token)
    return Date.now() / 1000 > payload.exp - bufferSeconds
  } catch {
    return true
  }
}
