import { describe, it, expect, vi } from "vitest"
import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { server } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import "@/lib/i18n"
import { VoicemailPage } from "../voicemail-page"
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

function setupVoicemailHandlers() {
  server.use(
    http.get(`/api/v1/tenants/:tenantId/voicemail-boxes`, () => {
      return HttpResponse.json([
        {
          id: "vm-001",
          tenant_id: tenantId,
          mailbox_number: "101",
          greeting_type: "default",
          email_notification: true,
          notification_email: "admin@test.com",
          max_messages: 100,
          is_active: true,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
        },
        {
          id: "vm-002",
          tenant_id: tenantId,
          mailbox_number: "102",
          greeting_type: "custom",
          email_notification: false,
          notification_email: null,
          max_messages: 50,
          is_active: false,
          created_at: "2025-01-02T00:00:00Z",
          updated_at: "2025-01-02T00:00:00Z",
        },
      ])
    }),

    http.get(`/api/v1/tenants/:tenantId/voicemail-boxes/:boxId/messages`, () => {
      return HttpResponse.json([
        {
          id: "msg-001",
          tenant_id: tenantId,
          voicemail_box_id: "vm-001",
          caller_number: "+15559876543",
          caller_name: "Alice Smith",
          duration_seconds: 30,
          storage_path: "/storage/msg-001.wav",
          storage_bucket: "voicemail",
          file_size_bytes: 48000,
          format: "wav",
          sha256_hash: null,
          is_read: false,
          is_urgent: true,
          folder: "inbox",
          call_id: "call-100",
          email_sent: true,
          is_active: true,
          created_at: "2025-01-15T10:00:00Z",
          updated_at: "2025-01-15T10:00:00Z",
        },
        {
          id: "msg-002",
          tenant_id: tenantId,
          voicemail_box_id: "vm-001",
          caller_number: "+15551112222",
          caller_name: "",
          duration_seconds: 15,
          storage_path: "/storage/msg-002.wav",
          storage_bucket: "voicemail",
          file_size_bytes: 24000,
          format: "wav",
          sha256_hash: null,
          is_read: true,
          is_urgent: false,
          folder: "inbox",
          call_id: "call-101",
          email_sent: false,
          is_active: true,
          created_at: "2025-01-15T11:00:00Z",
          updated_at: "2025-01-15T11:00:00Z",
        },
      ])
    })
  )
}

describe("VoicemailPage", () => {
  beforeEach(() => {
    useAuthStore.getState().login(testAccessToken, testRefreshToken)
    useAuthStore.getState().setActiveTenant(tenantId)
    setupVoicemailHandlers()
  })

  afterEach(() => {
    useAuthStore.getState().logout()
  })

  it("renders the page title", async () => {
    renderWithProviders(<VoicemailPage />)
    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1, name: "Voicemail" })).toBeInTheDocument()
    })
  })

  it("renders the page description after boxes load", async () => {
    renderWithProviders(<VoicemailPage />)
    await waitFor(() => {
      expect(screen.getByText("Manage voicemail boxes and messages")).toBeInTheDocument()
    })
  })

  it("renders the create voicemail box button", async () => {
    renderWithProviders(<VoicemailPage />)
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Create Voicemail Box/i })).toBeInTheDocument()
    })
  })

  it("displays voicemail box numbers after loading", async () => {
    renderWithProviders(<VoicemailPage />)
    await waitFor(() => {
      expect(screen.getByText(/Box 101/)).toBeInTheDocument()
    })
    expect(screen.getByText(/Box 102/)).toBeInTheDocument()
  })

  it("shows inactive badge for inactive boxes", async () => {
    renderWithProviders(<VoicemailPage />)
    await waitFor(() => {
      expect(screen.getByText("Inactive")).toBeInTheDocument()
    })
  })

  it("shows select box message before selecting a box", async () => {
    renderWithProviders(<VoicemailPage />)
    await waitFor(() => {
      expect(screen.getByText("Select a voicemail box to view messages")).toBeInTheDocument()
    })
  })

  it("shows messages after selecting a voicemail box", async () => {
    const user = userEvent.setup()
    renderWithProviders(<VoicemailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Box 101/)).toBeInTheDocument()
    })

    // Click the first box card
    await user.click(screen.getByText(/Box 101/))

    await waitFor(() => {
      expect(screen.getByText("Alice Smith")).toBeInTheDocument()
    })
  })

  it("shows urgent badge on urgent messages", async () => {
    const user = userEvent.setup()
    renderWithProviders(<VoicemailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Box 101/)).toBeInTheDocument()
    })

    await user.click(screen.getByText(/Box 101/))

    await waitFor(() => {
      expect(screen.getByText("Urgent")).toBeInTheDocument()
    })
  })

  it("shows Mark Read button for unread messages", async () => {
    const user = userEvent.setup()
    renderWithProviders(<VoicemailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Box 101/)).toBeInTheDocument()
    })

    await user.click(screen.getByText(/Box 101/))

    await waitFor(() => {
      expect(screen.getByText("Mark Read")).toBeInTheDocument()
    })
  })

  it("shows loading skeletons while boxes are loading", () => {
    // Override handler to be slow
    server.use(
      http.get(`/api/v1/tenants/:tenantId/voicemail-boxes`, async () => {
        await new Promise((resolve) => setTimeout(resolve, 500))
        return HttpResponse.json([])
      })
    )
    renderWithProviders(<VoicemailPage />)
    const skeletons = document.querySelectorAll('[class*="animate-pulse"]')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it("shows empty state when no voicemail boxes exist", async () => {
    server.use(
      http.get(`/api/v1/tenants/:tenantId/voicemail-boxes`, () => {
        return HttpResponse.json([])
      })
    )
    renderWithProviders(<VoicemailPage />)
    await waitFor(() => {
      expect(screen.getByText("No voicemail boxes yet")).toBeInTheDocument()
    })
  })
})
