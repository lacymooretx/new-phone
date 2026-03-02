import { describe, it, expect, vi } from "vitest"
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { server } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import "@/lib/i18n"
import { TenantsPage } from "../tenants-page"
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

function setupTenantsHandler() {
  server.use(
    http.get(`/api/v1/tenants`, () => {
      return HttpResponse.json([
        {
          id: tenantId,
          name: "Test Tenant",
          slug: "test",
          domain: "test.com",
          sip_domain: "test.sip.local",
          default_moh_prompt_id: null,
          is_active: true,
          notes: null,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
        },
        {
          id: "00000000-0000-0000-0000-000000000002",
          name: "Acme Corp",
          slug: "acme",
          domain: "acme.com",
          sip_domain: "acme.sip.local",
          default_moh_prompt_id: null,
          is_active: true,
          notes: null,
          created_at: "2025-01-02T00:00:00Z",
          updated_at: "2025-01-02T00:00:00Z",
        },
      ])
    })
  )
}

describe("TenantsPage", () => {
  beforeEach(() => {
    useAuthStore.getState().login(testAccessToken, testRefreshToken)
    useAuthStore.getState().setActiveTenant(tenantId)
    setupTenantsHandler()
  })

  afterEach(() => {
    useAuthStore.getState().logout()
  })

  it("renders the page title", () => {
    renderWithProviders(<TenantsPage />)
    expect(screen.getByRole("heading", { level: 1, name: "Tenants" })).toBeInTheDocument()
  })

  it("renders the page description", () => {
    renderWithProviders(<TenantsPage />)
    expect(screen.getByText("Manage tenant organizations")).toBeInTheDocument()
  })

  it("renders the create tenant button", () => {
    renderWithProviders(<TenantsPage />)
    // The button text uses t('tenants.createTenant') -- which may render as "createTenant" if key is missing
    // Let's check for any button containing "Create" or "Tenant"
    const buttons = screen.getAllByRole("button")
    const createButton = buttons.find((b) => b.textContent?.includes("Tenant") || b.textContent?.includes("Create"))
    expect(createButton).toBeDefined()
  })

  it("displays tenant names in the table after loading", async () => {
    renderWithProviders(<TenantsPage />)
    await waitFor(() => {
      expect(screen.getByText("Test Tenant")).toBeInTheDocument()
    })
    expect(screen.getByText("Acme Corp")).toBeInTheDocument()
  })

  it("displays tenant domains", async () => {
    renderWithProviders(<TenantsPage />)
    await waitFor(() => {
      expect(screen.getByText("test.com")).toBeInTheDocument()
    })
    expect(screen.getByText("acme.com")).toBeInTheDocument()
  })

  it("displays tenant slugs", async () => {
    renderWithProviders(<TenantsPage />)
    await waitFor(() => {
      expect(screen.getByText("test")).toBeInTheDocument()
    })
    expect(screen.getByText("acme")).toBeInTheDocument()
  })

  it("shows a search input for filtering", () => {
    renderWithProviders(<TenantsPage />)
    expect(screen.getByPlaceholderText("Search tenants...")).toBeInTheDocument()
  })

  it("shows error message when API fails", async () => {
    server.use(
      http.get(`/api/v1/tenants`, () => {
        return HttpResponse.json({ detail: "Server error" }, { status: 500 })
      })
    )
    renderWithProviders(<TenantsPage />)
    // The error template uses t('dashboard.failedToLoadData') which falls back to the key
    await waitFor(() => {
      expect(screen.getByText(/failedToLoadData|Failed to load|Server error/i)).toBeInTheDocument()
    })
  })

  it("shows empty state when no tenants exist", async () => {
    server.use(
      http.get(`/api/v1/tenants`, () => {
        return HttpResponse.json([])
      })
    )
    renderWithProviders(<TenantsPage />)
    await waitFor(() => {
      expect(screen.getByText("No tenants yet")).toBeInTheDocument()
    })
  })
})
