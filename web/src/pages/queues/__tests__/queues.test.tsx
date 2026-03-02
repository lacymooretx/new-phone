import { describe, it, expect, vi } from "vitest"
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { server } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import "@/lib/i18n"
import { QueuesPage } from "../queues-page"
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

function setupQueuesHandler() {
  server.use(
    http.get(`/api/v1/tenants/:tenantId/queues`, () => {
      return HttpResponse.json([
        {
          id: "queue-001",
          tenant_id: tenantId,
          name: "Support Queue",
          queue_number: "700",
          description: "Customer support queue",
          strategy: "longest-idle-agent",
          moh_prompt_id: null,
          max_wait_time: 300,
          max_wait_time_with_no_agent: 60,
          tier_rules_apply: false,
          tier_rule_wait_second: 15,
          tier_rule_wait_multiply_level: false,
          tier_rule_no_agent_no_wait: false,
          discard_abandoned_after: 60,
          abandoned_resume_allowed: false,
          caller_exit_key: "#",
          wrapup_time: 10,
          ring_timeout: 20,
          announce_frequency: 30,
          announce_prompt_id: null,
          overflow_destination_type: null,
          overflow_destination_id: null,
          record_calls: true,
          enabled: true,
          disposition_required: false,
          disposition_code_list_id: null,
          members: [],
          is_active: true,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
        },
        {
          id: "queue-002",
          tenant_id: tenantId,
          name: "Sales Queue",
          queue_number: "701",
          description: null,
          strategy: "ring-all",
          moh_prompt_id: null,
          max_wait_time: 300,
          max_wait_time_with_no_agent: 60,
          tier_rules_apply: false,
          tier_rule_wait_second: 15,
          tier_rule_wait_multiply_level: false,
          tier_rule_no_agent_no_wait: false,
          discard_abandoned_after: 60,
          abandoned_resume_allowed: false,
          caller_exit_key: null,
          wrapup_time: 10,
          ring_timeout: 20,
          announce_frequency: 30,
          announce_prompt_id: null,
          overflow_destination_type: null,
          overflow_destination_id: null,
          record_calls: false,
          enabled: true,
          disposition_required: false,
          disposition_code_list_id: null,
          members: [],
          is_active: true,
          created_at: "2025-01-02T00:00:00Z",
          updated_at: "2025-01-02T00:00:00Z",
        },
      ])
    })
  )
}

describe("QueuesPage", () => {
  beforeEach(() => {
    useAuthStore.getState().login(testAccessToken, testRefreshToken)
    useAuthStore.getState().setActiveTenant(tenantId)
    setupQueuesHandler()
  })

  afterEach(() => {
    useAuthStore.getState().logout()
  })

  it("renders the page title", () => {
    renderWithProviders(<QueuesPage />)
    expect(screen.getByRole("heading", { level: 1, name: "Queues" })).toBeInTheDocument()
  })

  it("renders the page description", () => {
    renderWithProviders(<QueuesPage />)
    expect(screen.getByText("Manage call queues")).toBeInTheDocument()
  })

  it("renders the create queue button", () => {
    renderWithProviders(<QueuesPage />)
    expect(screen.getByRole("button", { name: /Create Queue/i })).toBeInTheDocument()
  })

  it("displays queue names in the table after loading", async () => {
    renderWithProviders(<QueuesPage />)
    await waitFor(() => {
      expect(screen.getByText("Support Queue")).toBeInTheDocument()
    })
    expect(screen.getByText("Sales Queue")).toBeInTheDocument()
  })

  it("displays queue numbers from mock data", async () => {
    renderWithProviders(<QueuesPage />)
    await waitFor(() => {
      expect(screen.getByText("700")).toBeInTheDocument()
    })
    expect(screen.getByText("701")).toBeInTheDocument()
  })

  it("shows a search input for filtering", () => {
    renderWithProviders(<QueuesPage />)
    expect(screen.getByPlaceholderText("Search queues...")).toBeInTheDocument()
  })

  it("shows error message when API fails", async () => {
    server.use(
      http.get(`/api/v1/tenants/:tenantId/queues`, () => {
        return HttpResponse.json({ detail: "Server error" }, { status: 500 })
      })
    )
    renderWithProviders(<QueuesPage />)
    await waitFor(() => {
      expect(screen.getByText(/Failed to load/i)).toBeInTheDocument()
    })
  })

  it("shows empty state when no queues exist", async () => {
    server.use(
      http.get(`/api/v1/tenants/:tenantId/queues`, () => {
        return HttpResponse.json([])
      })
    )
    renderWithProviders(<QueuesPage />)
    await waitFor(() => {
      expect(screen.getByText("No queues yet")).toBeInTheDocument()
    })
  })
})
