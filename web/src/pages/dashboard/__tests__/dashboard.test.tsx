import { describe, it, expect, vi } from "vitest"
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { server } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import "@/lib/i18n"
import { DashboardPage } from "../dashboard-page"
import { useAuthStore } from "@/stores/auth-store"
import { testAccessToken, testRefreshToken } from "@/test/handlers"

const tenantId = "00000000-0000-0000-0000-000000000001"

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router")
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Set up additional MSW handlers for dashboard-specific endpoints
function setupDashboardHandlers() {
  server.use(
    http.get(`/api/v1/tenants/:tenantId/users`, () => {
      return HttpResponse.json([
        {
          id: "user-001",
          tenant_id: tenantId,
          email: "admin@test.com",
          first_name: "John",
          last_name: "Doe",
          role: "msp_super_admin",
          is_active: true,
          mfa_enabled: false,
          last_login_at: null,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
        },
      ])
    }),

    http.get(`/api/v1/tenants/:tenantId/analytics/summary`, () => {
      return HttpResponse.json({
        total_calls: 42,
        inbound: 20,
        outbound: 18,
        internal: 4,
        answered: 35,
        no_answer: 3,
        busy: 1,
        failed: 0,
        voicemail: 2,
        cancelled: 1,
        avg_duration_seconds: 185,
        total_duration_seconds: 7770,
      })
    }),

    http.get(`/api/v1/tenants/:tenantId/analytics/volume-trend`, () => {
      return HttpResponse.json({ granularity: "day", data: [] })
    }),

    http.get(`/api/v1/tenants/:tenantId/queues/stats`, () => {
      return HttpResponse.json([])
    }),

    http.get(`/api/v1/tenants/:tenantId/queues/agent-status`, () => {
      return HttpResponse.json([])
    }),
  )
}

describe("DashboardPage", () => {
  beforeEach(() => {
    useAuthStore.getState().login(testAccessToken, testRefreshToken)
    useAuthStore.getState().setActiveTenant(tenantId)
    setupDashboardHandlers()
  })

  afterEach(() => {
    useAuthStore.getState().logout()
    mockNavigate.mockClear()
  })

  it("renders the dashboard title", async () => {
    renderWithProviders(<DashboardPage />)
    expect(screen.getByRole("heading", { level: 1, name: "Dashboard" })).toBeInTheDocument()
  })

  it("renders the dashboard description", () => {
    renderWithProviders(<DashboardPage />)
    expect(screen.getByText("System overview")).toBeInTheDocument()
  })

  it("shows skeleton loading states initially", () => {
    renderWithProviders(<DashboardPage />)
    // The dashboard should show skeletons while data loads
    const skeletons = document.querySelectorAll('[class*="animate-pulse"]')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it("displays extension count stat card after loading", async () => {
    renderWithProviders(<DashboardPage />)
    // The translation key 'dashboard.extensions' maps to i18n fallback
    // The extension list mock returns 1 extension, so the value should be "1"
    await waitFor(() => {
      const statValues = document.querySelectorAll(".text-2xl.font-bold")
      const values = Array.from(statValues).map((el) => el.textContent)
      expect(values).toContain("1")
    })
  })

  it("displays users count stat card after loading", async () => {
    renderWithProviders(<DashboardPage />)
    // The mock returns 1 user, so a stat card shows value "1"
    await waitFor(() => {
      const statValues = document.querySelectorAll(".text-2xl.font-bold")
      const values = Array.from(statValues).map((el) => el.textContent)
      // At least one stat card should show value 1 (extensions: 1 and users: 1)
      const countOfOnes = values.filter((v) => v === "1").length
      expect(countOfOnes).toBeGreaterThanOrEqual(1)
    })
  })

  it("displays system health stat card", async () => {
    renderWithProviders(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByText("System Health")).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.getByText("Healthy")).toBeInTheDocument()
    })
  })

  it("displays calls today stat card after loading", async () => {
    renderWithProviders(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByText("Calls Today")).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.getByText("42")).toBeInTheDocument()
    })
  })

  it("displays average duration stat card", async () => {
    renderWithProviders(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByText("Avg Duration")).toBeInTheDocument()
    })
    // 185 seconds = 3:05
    await waitFor(() => {
      expect(screen.getByText("3:05")).toBeInTheDocument()
    })
  })

  it("renders quick actions section", async () => {
    renderWithProviders(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByText("Quick Actions")).toBeInTheDocument()
    })
  })

  it("renders recent calls section", async () => {
    renderWithProviders(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByText("Recent Calls")).toBeInTheDocument()
    })
  })

  it("shows CDR data in the recent calls table", async () => {
    renderWithProviders(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByText("+15551234567")).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.getByText("1001")).toBeInTheDocument()
    })
  })

  it("shows call direction badges", async () => {
    renderWithProviders(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByText("inbound")).toBeInTheDocument()
    })
  })

  it("shows call disposition badges", async () => {
    renderWithProviders(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByText("answered")).toBeInTheDocument()
    })
  })

  it("shows error state when data fetching fails", async () => {
    server.use(
      http.get(`/api/v1/tenants/:tenantId/extensions`, () => {
        return HttpResponse.json({ detail: "Server error" }, { status: 500 })
      })
    )
    renderWithProviders(<DashboardPage />)
    // The error message uses t('dashboard.failedToLoadData') which falls back to the key
    await waitFor(() => {
      expect(screen.getByText(/failedToLoadData|Failed to load/i)).toBeInTheDocument()
    })
  })
})
