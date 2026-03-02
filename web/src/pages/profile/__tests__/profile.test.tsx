import { describe, it, expect, vi } from "vitest"
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { server } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import "@/lib/i18n"
import { ProfilePage } from "../profile-page"
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

function setupProfileHandlers() {
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
          last_login_at: "2025-01-15T10:00:00Z",
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
        },
      ])
    }),

    http.post(`/api/v1/auth/change-password`, () => {
      return HttpResponse.json({ success: true })
    }),

    http.post(`/api/v1/auth/mfa/setup`, () => {
      return HttpResponse.json({
        totp_uri: "otpauth://totp/AspendoraConnect:admin@test.com?secret=TESTSECRET&issuer=AspendoraConnect",
        backup_codes: ["12345678", "87654321", "11111111", "22222222"],
      })
    }),
  )
}

describe("ProfilePage", () => {
  beforeEach(() => {
    useAuthStore.getState().login(testAccessToken, testRefreshToken)
    useAuthStore.getState().setActiveTenant(tenantId)
    setupProfileHandlers()
  })

  afterEach(() => {
    useAuthStore.getState().logout()
  })

  it("renders the page title", async () => {
    renderWithProviders(<ProfilePage />)
    // May show a loading skeleton first, then the real heading
    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1, name: "Profile" })).toBeInTheDocument()
    })
  })

  it("shows loading skeleton initially", () => {
    renderWithProviders(<ProfilePage />)
    const skeletons = document.querySelectorAll('[class*="animate-pulse"]')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it("displays the personal information card after loading", async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByText("Personal Information")).toBeInTheDocument()
    })
  })

  it("shows first name field with user data", async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByText("First Name")).toBeInTheDocument()
    })
    await waitFor(() => {
      const firstNameInput = screen.getByDisplayValue("John")
      expect(firstNameInput).toBeInTheDocument()
    })
  })

  it("shows last name field with user data", async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      const lastNameInput = screen.getByDisplayValue("Doe")
      expect(lastNameInput).toBeInTheDocument()
    })
  })

  it("shows email as disabled input", async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      const emailInput = screen.getByDisplayValue("admin@test.com")
      expect(emailInput).toBeInTheDocument()
      expect(emailInput).toBeDisabled()
    })
  })

  it("shows role badge", async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByText("Msp Super Admin")).toBeInTheDocument()
    })
  })

  it("shows save changes button", async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Save Changes" })).toBeInTheDocument()
    })
  })

  it("displays the security card", async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByText("Security")).toBeInTheDocument()
    })
  })

  it("shows change password button", async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Change Password" })).toBeInTheDocument()
    })
  })

  it("shows MFA section", async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByText("Multi-Factor Authentication")).toBeInTheDocument()
    })
  })

  it("shows MFA not enabled state when MFA is off", async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByText("MFA Not Enabled")).toBeInTheDocument()
    })
  })

  it("shows enable MFA button when MFA is off", async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Enable MFA" })).toBeInTheDocument()
    })
  })

  it("shows MFA enabled state when user has MFA", async () => {
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
        ])
      })
    )
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByText("MFA Enabled")).toBeInTheDocument()
    })
  })

  it("shows language selection card", async () => {
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByText("Language")).toBeInTheDocument()
    })
  })

  it("shows unable to load message when user not found", async () => {
    server.use(
      http.get(`/api/v1/tenants/:tenantId/users`, () => {
        return HttpResponse.json([
          {
            id: "different-user",
            tenant_id: tenantId,
            email: "other@test.com",
            first_name: "Other",
            last_name: "User",
            role: "tenant_user",
            is_active: true,
            mfa_enabled: false,
            last_login_at: null,
            created_at: "2025-01-01T00:00:00Z",
            updated_at: "2025-01-01T00:00:00Z",
          },
        ])
      })
    )
    renderWithProviders(<ProfilePage />)
    await waitFor(() => {
      expect(screen.getByText("Unable to load profile.")).toBeInTheDocument()
    })
  })
})
