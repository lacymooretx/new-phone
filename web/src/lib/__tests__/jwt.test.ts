import { describe, it, expect } from "vitest"
import { decodeJwtPayload, isTokenExpired } from "../jwt"

function makeToken(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }))
  const body = btoa(JSON.stringify(payload))
  const sig = btoa("test-signature")
  return `${header}.${body}.${sig}`
}

describe("decodeJwtPayload", () => {
  it("decodes a valid JWT payload", () => {
    const token = makeToken({
      sub: "user-123",
      tenant_id: "tenant-456",
      role: "msp_super_admin",
      type: "access",
      exp: 1700000000,
      iat: 1699996400,
    })

    const payload = decodeJwtPayload(token)
    expect(payload.sub).toBe("user-123")
    expect(payload.tenant_id).toBe("tenant-456")
    expect(payload.role).toBe("msp_super_admin")
    expect(payload.type).toBe("access")
    expect(payload.exp).toBe(1700000000)
  })

  it("throws on invalid token format", () => {
    expect(() => decodeJwtPayload("not-a-jwt")).toThrow("Invalid JWT")
  })

  it("throws on malformed payload", () => {
    expect(() => decodeJwtPayload("a.!!!.c")).toThrow()
  })
})

describe("isTokenExpired", () => {
  it("returns false for a token expiring in the future", () => {
    const token = makeToken({
      sub: "user-123",
      tenant_id: "t1",
      role: "tenant_user",
      type: "access",
      exp: Math.floor(Date.now() / 1000) + 3600,
      iat: Math.floor(Date.now() / 1000),
    })
    expect(isTokenExpired(token)).toBe(false)
  })

  it("returns true for an expired token", () => {
    const token = makeToken({
      sub: "user-123",
      tenant_id: "t1",
      role: "tenant_user",
      type: "access",
      exp: Math.floor(Date.now() / 1000) - 60,
      iat: Math.floor(Date.now() / 1000) - 3660,
    })
    expect(isTokenExpired(token)).toBe(true)
  })

  it("returns true for a token within the buffer window", () => {
    const token = makeToken({
      sub: "user-123",
      tenant_id: "t1",
      role: "tenant_user",
      type: "access",
      exp: Math.floor(Date.now() / 1000) + 10,
      iat: Math.floor(Date.now() / 1000),
    })
    expect(isTokenExpired(token, 30)).toBe(true)
  })

  it("returns true for garbage input", () => {
    expect(isTokenExpired("not-a-token")).toBe(true)
  })
})
