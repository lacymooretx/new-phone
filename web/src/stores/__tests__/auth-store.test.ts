import { describe, it, expect, beforeEach, vi } from "vitest"
import { useAuthStore } from "../auth-store"

function makeToken(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }))
  const body = btoa(JSON.stringify(payload))
  const sig = btoa("test-signature")
  return `${header}.${body}.${sig}`
}

const testPayload = {
  sub: "user-001",
  tenant_id: "00000000-0000-0000-0000-000000000001",
  role: "msp_super_admin",
  type: "access",
  exp: Math.floor(Date.now() / 1000) + 3600,
  iat: Math.floor(Date.now() / 1000),
}

const accessToken = makeToken(testPayload)
const refreshToken = "refresh-token-abc"

// Mock localStorage since jsdom doesn't provide a fully functional one
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string): string | null => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value }),
    removeItem: vi.fn((key: string) => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
    get length() { return Object.keys(store).length },
    key: vi.fn((i: number) => Object.keys(store)[i] ?? null),
  }
})()

Object.defineProperty(globalThis, "localStorage", { value: localStorageMock, writable: true })

describe("auth-store", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: null,
      refreshToken: null,
      user: null,
      activeTenantId: null,
      isAuthenticated: false,
      isBootstrapping: true,
    })
    localStorageMock.clear()
    vi.clearAllMocks()
  })

  // ── login ──────────────────────────────────────────────────────────
  describe("login()", () => {
    it("sets isAuthenticated, user, and stores refreshToken in localStorage", () => {
      useAuthStore.getState().login(accessToken, refreshToken)

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(true)
      expect(state.user).not.toBeNull()
      expect(state.accessToken).toBe(accessToken)
      expect(state.refreshToken).toBe(refreshToken)
      expect(localStorageMock.setItem).toHaveBeenCalledWith("refresh_token", refreshToken)
    })

    it("decodes user from JWT (sub, tenant_id, role)", () => {
      useAuthStore.getState().login(accessToken, refreshToken)

      const user = useAuthStore.getState().user
      expect(user).toEqual({
        id: testPayload.sub,
        tenantId: testPayload.tenant_id,
        role: testPayload.role,
      })
    })
  })

  // ── logout ─────────────────────────────────────────────────────────
  describe("logout()", () => {
    it("clears all state and removes refreshToken from localStorage", () => {
      useAuthStore.getState().login(accessToken, refreshToken)
      expect(useAuthStore.getState().isAuthenticated).toBe(true)

      useAuthStore.getState().logout()

      const state = useAuthStore.getState()
      expect(state.accessToken).toBeNull()
      expect(state.refreshToken).toBeNull()
      expect(state.user).toBeNull()
      expect(state.activeTenantId).toBeNull()
      expect(state.isAuthenticated).toBe(false)
      expect(state.isBootstrapping).toBe(false)
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("refresh_token")
    })
  })

  // ── setTokens ──────────────────────────────────────────────────────
  describe("setTokens()", () => {
    it("preserves existing activeTenantId", () => {
      const customTenantId = "00000000-0000-0000-0000-000000000099"
      useAuthStore.setState({ activeTenantId: customTenantId })

      useAuthStore.getState().setTokens(accessToken, refreshToken)

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(true)
      expect(state.activeTenantId).toBe(customTenantId)
      expect(state.user).not.toBeNull()
      expect(localStorageMock.setItem).toHaveBeenCalledWith("refresh_token", refreshToken)
    })
  })

  // ── bootstrap ──────────────────────────────────────────────────────
  describe("bootstrap()", () => {
    it("with valid stored token refreshes and authenticates", async () => {
      localStorageMock.getItem.mockReturnValueOnce("stored-refresh-token")

      // Mock fetch to return valid tokens
      const originalFetch = globalThis.fetch
      globalThis.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: accessToken,
          refresh_token: "new-refresh-token",
        }),
      })

      await useAuthStore.getState().bootstrap()

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(true)
      expect(state.user).not.toBeNull()
      expect(state.isBootstrapping).toBe(false)

      globalThis.fetch = originalFetch
    })

    it("with no stored token sets isBootstrapping to false", async () => {
      localStorageMock.getItem.mockReturnValueOnce(null)

      await useAuthStore.getState().bootstrap()

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(false)
      expect(state.isBootstrapping).toBe(false)
      expect(state.user).toBeNull()
    })

    it("with failed refresh calls logout", async () => {
      localStorageMock.getItem.mockReturnValueOnce("stored-refresh-token")

      const originalFetch = globalThis.fetch
      globalThis.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Token expired" }),
      })

      await useAuthStore.getState().bootstrap()

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(false)
      expect(state.accessToken).toBeNull()
      expect(state.isBootstrapping).toBe(false)

      globalThis.fetch = originalFetch
    })
  })

  // ── setActiveTenant ────────────────────────────────────────────────
  describe("setActiveTenant()", () => {
    it("updates activeTenantId", () => {
      const tenantId = "00000000-0000-0000-0000-000000000055"
      useAuthStore.getState().setActiveTenant(tenantId)

      expect(useAuthStore.getState().activeTenantId).toBe(tenantId)
    })
  })
})
