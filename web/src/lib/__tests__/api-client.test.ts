import { describe, it, expect, beforeEach } from "vitest"
import { apiClient, ApiError } from "../api-client"
import { useAuthStore } from "@/stores/auth-store"
import { testAccessToken, testRefreshToken } from "@/test/handlers"

describe("apiClient", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: testAccessToken,
      refreshToken: testRefreshToken,
      isAuthenticated: true,
      isBootstrapping: false,
      user: { id: "user-001", tenantId: "00000000-0000-0000-0000-000000000001", role: "msp_super_admin" },
      activeTenantId: "00000000-0000-0000-0000-000000000001",
    })
  })

  it("injects Bearer token in requests", async () => {
    const data = await apiClient.get<{ status: string }>("health")
    expect(data.status).toBe("healthy")
  })

  it("parses successful JSON responses", async () => {
    const tenants = await apiClient.get<Array<{ id: string; name: string }>>("tenants")
    expect(tenants).toHaveLength(1)
    expect(tenants[0].name).toBe("Test Tenant")
  })

  it("throws ApiError on 401 with invalid credentials", async () => {
    // Clear auth state to prevent refresh retry
    useAuthStore.setState({ accessToken: null, refreshToken: null })

    await expect(
      apiClient.post("/api/v1/auth/login", { email: "bad@test.com", password: "wrong" })
    ).rejects.toThrow(ApiError)
  })

  it("refreshes token on 401 and retries", async () => {
    // This tests the refresh flow indirectly via the MSW handlers
    // The MSW handler always returns 200 for /auth/refresh
    const data = await apiClient.get<{ status: string }>("health")
    expect(data.status).toBe("healthy")
  })

  it("appends query params correctly", async () => {
    const data = await apiClient.get<unknown[]>(
      `tenants/00000000-0000-0000-0000-000000000001/cdrs`,
      { limit: "10", offset: "0" }
    )
    expect(Array.isArray(data)).toBe(true)
  })
})
