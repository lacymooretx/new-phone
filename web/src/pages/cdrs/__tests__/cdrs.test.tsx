import { describe, it, expect, vi } from "vitest"
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { server } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import "@/lib/i18n"
import { CdrsPage } from "../cdrs-page"
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

function setupCdrsHandler() {
  server.use(
    http.get(`/api/v1/tenants/:tenantId/cdrs`, () => {
      return HttpResponse.json([
        {
          id: "cdr-001",
          tenant_id: tenantId,
          call_id: "call-001",
          direction: "inbound",
          caller_number: "+15551234567",
          caller_name: "Test Caller",
          called_number: "1001",
          extension_id: null,
          did_id: null,
          trunk_id: null,
          ring_group_id: null,
          queue_id: null,
          disposition: "answered",
          hangup_cause: null,
          duration_seconds: 120,
          billable_seconds: 115,
          ring_seconds: 5,
          start_time: "2025-01-15T10:00:00Z",
          answer_time: "2025-01-15T10:00:05Z",
          end_time: "2025-01-15T10:02:00Z",
          has_recording: true,
          created_at: "2025-01-15T10:02:00Z",
          agent_disposition_code_id: null,
          agent_disposition_notes: null,
          disposition_entered_at: null,
          agent_disposition_label: null,
          site_id: null,
          compliance_score: null,
          compliance_evaluation_id: null,
        },
        {
          id: "cdr-002",
          tenant_id: tenantId,
          call_id: "call-002",
          direction: "outbound",
          caller_number: "1001",
          caller_name: "John Doe",
          called_number: "+15559876543",
          extension_id: "ext-001",
          did_id: null,
          trunk_id: null,
          ring_group_id: null,
          queue_id: null,
          disposition: "no_answer",
          hangup_cause: null,
          duration_seconds: 30,
          billable_seconds: 0,
          ring_seconds: 30,
          start_time: "2025-01-15T11:00:00Z",
          answer_time: null,
          end_time: "2025-01-15T11:00:30Z",
          has_recording: false,
          created_at: "2025-01-15T11:00:30Z",
          agent_disposition_code_id: null,
          agent_disposition_notes: null,
          disposition_entered_at: null,
          agent_disposition_label: null,
          site_id: null,
          compliance_score: null,
          compliance_evaluation_id: null,
        },
      ])
    })
  )
}

describe("CdrsPage", () => {
  beforeEach(() => {
    useAuthStore.getState().login(testAccessToken, testRefreshToken)
    useAuthStore.getState().setActiveTenant(tenantId)
    setupCdrsHandler()
  })

  afterEach(() => {
    useAuthStore.getState().logout()
  })

  it("renders the page title", () => {
    renderWithProviders(<CdrsPage />)
    expect(screen.getByRole("heading", { level: 1, name: "Call History" })).toBeInTheDocument()
  })

  it("renders the page description", () => {
    renderWithProviders(<CdrsPage />)
    expect(screen.getByText("View call detail records")).toBeInTheDocument()
  })

  it("renders the export button", () => {
    renderWithProviders(<CdrsPage />)
    expect(screen.getByRole("button", { name: /Export/i })).toBeInTheDocument()
  })

  it("displays CDR caller numbers after loading", async () => {
    renderWithProviders(<CdrsPage />)
    await waitFor(() => {
      expect(screen.getByText("+15551234567")).toBeInTheDocument()
    })
  })

  it("displays CDR called numbers", async () => {
    renderWithProviders(<CdrsPage />)
    // "1001" appears as both caller_number in cdr-002 and called_number in cdr-001
    await waitFor(() => {
      const cells = screen.getAllByText("1001")
      expect(cells.length).toBeGreaterThanOrEqual(1)
    })
    expect(screen.getByText("+15559876543")).toBeInTheDocument()
  })

  it("displays call dispositions", async () => {
    renderWithProviders(<CdrsPage />)
    await waitFor(() => {
      expect(screen.getByText("answered")).toBeInTheDocument()
    })
    expect(screen.getByText("no_answer")).toBeInTheDocument()
  })

  it("displays call directions", async () => {
    renderWithProviders(<CdrsPage />)
    await waitFor(() => {
      expect(screen.getByText("inbound")).toBeInTheDocument()
    })
    expect(screen.getByText("outbound")).toBeInTheDocument()
  })

  it("has date filter inputs", () => {
    renderWithProviders(<CdrsPage />)
    const dateInputs = document.querySelectorAll('input[type="date"]')
    expect(dateInputs.length).toBe(2)
  })

  it("has direction filter select", () => {
    renderWithProviders(<CdrsPage />)
    // The direction select renders a trigger button
    const triggers = screen.getAllByRole("combobox")
    expect(triggers.length).toBeGreaterThanOrEqual(1)
  })

  it("has toolbar with filter controls visible", () => {
    renderWithProviders(<CdrsPage />)
    // The CDR page uses manualPagination, so DataTable does not render the
    // global search input.  But the toolbar with date/direction/disposition
    // filters is rendered by the page itself.
    const dateInputs = document.querySelectorAll('input[type="date"]')
    expect(dateInputs.length).toBe(2)
  })

  it("shows error message when API fails", async () => {
    server.use(
      http.get(`/api/v1/tenants/:tenantId/cdrs`, () => {
        return HttpResponse.json({ detail: "Server error" }, { status: 500 })
      })
    )
    renderWithProviders(<CdrsPage />)
    await waitFor(() => {
      expect(screen.getByText(/Failed to load/i)).toBeInTheDocument()
    })
  })

  it("shows empty state when no CDRs exist", async () => {
    server.use(
      http.get(`/api/v1/tenants/:tenantId/cdrs`, () => {
        return HttpResponse.json([])
      })
    )
    renderWithProviders(<CdrsPage />)
    await waitFor(() => {
      expect(screen.getByText("No calls recorded yet")).toBeInTheDocument()
    })
  })
})
