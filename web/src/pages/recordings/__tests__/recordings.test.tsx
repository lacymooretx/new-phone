import { describe, it, expect, vi } from "vitest"
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { server } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import "@/lib/i18n"
import { RecordingsPage } from "../recordings-page"
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

function setupRecordingsHandler() {
  server.use(
    http.get(`/api/v1/tenants/:tenantId/recordings`, () => {
      return HttpResponse.json([
        {
          id: "rec-001",
          tenant_id: tenantId,
          cdr_id: "cdr-001",
          call_id: "call-001",
          storage_path: "/recordings/rec-001.wav",
          storage_bucket: "recordings",
          file_size_bytes: 1024000,
          duration_seconds: 120,
          format: "wav",
          sample_rate: 16000,
          sha256_hash: null,
          recording_policy: "always",
          is_active: true,
          created_at: "2025-01-15T10:00:00Z",
        },
        {
          id: "rec-002",
          tenant_id: tenantId,
          cdr_id: "cdr-002",
          call_id: "call-002",
          storage_path: "/recordings/rec-002.wav",
          storage_bucket: "recordings",
          file_size_bytes: 512000,
          duration_seconds: 60,
          format: "wav",
          sample_rate: 16000,
          sha256_hash: null,
          recording_policy: "on-demand",
          is_active: true,
          created_at: "2025-01-15T11:00:00Z",
        },
      ])
    })
  )
}

describe("RecordingsPage", () => {
  beforeEach(() => {
    useAuthStore.getState().login(testAccessToken, testRefreshToken)
    useAuthStore.getState().setActiveTenant(tenantId)
    setupRecordingsHandler()
  })

  afterEach(() => {
    useAuthStore.getState().logout()
  })

  it("renders the page title", () => {
    renderWithProviders(<RecordingsPage />)
    expect(screen.getByRole("heading", { level: 1, name: "Recordings" })).toBeInTheDocument()
  })

  it("renders the page description", () => {
    renderWithProviders(<RecordingsPage />)
    expect(screen.getByText("Manage call recordings")).toBeInTheDocument()
  })

  it("renders an export button", () => {
    renderWithProviders(<RecordingsPage />)
    expect(screen.getByRole("button", { name: /Export/i })).toBeInTheDocument()
  })

  it("displays recording data after loading", async () => {
    renderWithProviders(<RecordingsPage />)
    // The call_id column uses .slice(0, 12) + "..." so "call-001" renders as "call-001..."
    await waitFor(() => {
      expect(screen.getByText("call-001...")).toBeInTheDocument()
    })
    expect(screen.getByText("call-002...")).toBeInTheDocument()
  })

  it("shows recording formats", async () => {
    renderWithProviders(<RecordingsPage />)
    await waitFor(() => {
      const wavCells = screen.getAllByText("wav")
      expect(wavCells.length).toBeGreaterThanOrEqual(1)
    })
  })

  it("shows recording policies", async () => {
    renderWithProviders(<RecordingsPage />)
    await waitFor(() => {
      expect(screen.getByText("always")).toBeInTheDocument()
    })
    expect(screen.getByText("on-demand")).toBeInTheDocument()
  })

  it("has date filter inputs", () => {
    renderWithProviders(<RecordingsPage />)
    const dateInputs = document.querySelectorAll('input[type="date"]')
    expect(dateInputs.length).toBe(2)
  })

  it("shows a search input for filtering", () => {
    renderWithProviders(<RecordingsPage />)
    expect(screen.getByPlaceholderText("Search recordings...")).toBeInTheDocument()
  })

  it("shows error message when API fails", async () => {
    server.use(
      http.get(`/api/v1/tenants/:tenantId/recordings`, () => {
        return HttpResponse.json({ detail: "Server error" }, { status: 500 })
      })
    )
    renderWithProviders(<RecordingsPage />)
    await waitFor(() => {
      expect(screen.getByText(/Failed to load/i)).toBeInTheDocument()
    })
  })

  it("shows empty state when no recordings exist", async () => {
    server.use(
      http.get(`/api/v1/tenants/:tenantId/recordings`, () => {
        return HttpResponse.json([])
      })
    )
    renderWithProviders(<RecordingsPage />)
    await waitFor(() => {
      expect(screen.getByText("No recordings yet")).toBeInTheDocument()
    })
  })
})
