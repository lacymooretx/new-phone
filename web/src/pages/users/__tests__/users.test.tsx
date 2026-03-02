import { describe, it, expect, vi } from "vitest"
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { server } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import "@/lib/i18n"
import { UsersPage } from "../users-page"
import { useAuthStore } from "@/stores/auth-store"
import { testAccessToken, testRefreshToken } from "@/test/handlers"

const tenantId = "00000000-0000-0000-0000-000000000001"

vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router")
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  }
})

function setupUsersHandler() {
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
          mfa_enabled: true,
          last_login_at: "2025-01-15T10:00:00Z",
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
        },
        {
          id: "user-002",
          tenant_id: tenantId,
          email: "jane@test.com",
          first_name: "Jane",
          last_name: "Smith",
          role: "tenant_admin",
          is_active: true,
          mfa_enabled: false,
          last_login_at: null,
          created_at: "2025-01-02T00:00:00Z",
          updated_at: "2025-01-02T00:00:00Z",
        },
      ])
    })
  )
}

describe("UsersPage", () => {
  beforeEach(() => {
    useAuthStore.getState().login(testAccessToken, testRefreshToken)
    useAuthStore.getState().setActiveTenant(tenantId)
    setupUsersHandler()
  })

  afterEach(() => {
    useAuthStore.getState().logout()
  })

  it("renders the page title", () => {
    renderWithProviders(<UsersPage />)
    expect(screen.getByRole("heading", { level: 1, name: "Users" })).toBeInTheDocument()
  })

  it("renders the page description", () => {
    renderWithProviders(<UsersPage />)
    expect(screen.getByText("Manage user accounts")).toBeInTheDocument()
  })

  it("renders the create user button", () => {
    renderWithProviders(<UsersPage />)
    expect(screen.getByRole("button", { name: /Create User/i })).toBeInTheDocument()
  })

  it("displays user emails in the table after loading", async () => {
    renderWithProviders(<UsersPage />)
    await waitFor(() => {
      expect(screen.getByText("admin@test.com")).toBeInTheDocument()
    })
    expect(screen.getByText("jane@test.com")).toBeInTheDocument()
  })

  it("displays user names from mock data", async () => {
    renderWithProviders(<UsersPage />)
    await waitFor(() => {
      expect(screen.getByText(/John/)).toBeInTheDocument()
    })
    expect(screen.getByText(/Jane/)).toBeInTheDocument()
  })

  it("shows role information", async () => {
    renderWithProviders(<UsersPage />)
    // The role column uses i18next.t('users.roles.msp_super_admin') = "MSP Super Admin"
    await waitFor(() => {
      expect(screen.getByText("MSP Super Admin")).toBeInTheDocument()
    })
  })

  it("shows a search input for filtering", () => {
    renderWithProviders(<UsersPage />)
    expect(screen.getByPlaceholderText("Search users...")).toBeInTheDocument()
  })

  it("shows error message when API fails", async () => {
    server.use(
      http.get(`/api/v1/tenants/:tenantId/users`, () => {
        return HttpResponse.json({ detail: "Unauthorized" }, { status: 403 })
      })
    )
    renderWithProviders(<UsersPage />)
    await waitFor(() => {
      expect(screen.getByText(/Failed to load/i)).toBeInTheDocument()
    })
  })

  it("shows empty state when no users exist", async () => {
    server.use(
      http.get(`/api/v1/tenants/:tenantId/users`, () => {
        return HttpResponse.json([])
      })
    )
    renderWithProviders(<UsersPage />)
    await waitFor(() => {
      expect(screen.getByText("No users yet")).toBeInTheDocument()
    })
  })
})
