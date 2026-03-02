import { describe, it, expect, vi } from "vitest"
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { server } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import "@/lib/i18n"
import { ExtensionsPage } from "../extensions-page"
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

describe("ExtensionsPage", () => {
  beforeEach(() => {
    useAuthStore.getState().login(testAccessToken, testRefreshToken)
    useAuthStore.getState().setActiveTenant(tenantId)
  })

  afterEach(() => {
    useAuthStore.getState().logout()
  })

  it("renders the page title", () => {
    renderWithProviders(<ExtensionsPage />)
    expect(screen.getByRole("heading", { level: 1, name: "Extensions" })).toBeInTheDocument()
  })

  it("renders the page description", () => {
    renderWithProviders(<ExtensionsPage />)
    expect(screen.getByText("Manage phone extensions")).toBeInTheDocument()
  })

  it("renders the create extension button", () => {
    renderWithProviders(<ExtensionsPage />)
    expect(screen.getByRole("button", { name: /Create Extension/i })).toBeInTheDocument()
  })

  it("displays extension data in the table after loading", async () => {
    renderWithProviders(<ExtensionsPage />)
    // The mock handler returns extension 1001 with name "John Doe"
    await waitFor(() => {
      expect(screen.getByText("1001")).toBeInTheDocument()
    })
  })

  it("displays extension CID name from mock data", async () => {
    renderWithProviders(<ExtensionsPage />)
    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument()
    })
  })

  it("shows a search input for filtering", () => {
    renderWithProviders(<ExtensionsPage />)
    expect(screen.getByPlaceholderText("Search extensions...")).toBeInTheDocument()
  })

  it("shows error message when API fails", async () => {
    server.use(
      http.get(`/api/v1/tenants/:tenantId/extensions`, () => {
        return HttpResponse.json({ detail: "Server error" }, { status: 500 })
      })
    )
    renderWithProviders(<ExtensionsPage />)
    await waitFor(() => {
      expect(screen.getByText(/Failed to load/i)).toBeInTheDocument()
    })
  })

  it("shows empty state when no extensions exist", async () => {
    server.use(
      http.get(`/api/v1/tenants/:tenantId/extensions`, () => {
        return HttpResponse.json([])
      })
    )
    renderWithProviders(<ExtensionsPage />)
    await waitFor(() => {
      expect(screen.getByText("No extensions yet")).toBeInTheDocument()
    })
  })

  it("shows loading state while fetching data", () => {
    renderWithProviders(<ExtensionsPage />)
    // DataTable shows skeleton rows when isLoading is true
    const skeletons = document.querySelectorAll('[class*="animate-pulse"]')
    expect(skeletons.length).toBeGreaterThan(0)
  })
})
