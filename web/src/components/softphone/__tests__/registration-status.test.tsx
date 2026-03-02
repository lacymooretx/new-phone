import type { ReactNode } from "react"
import { describe, it, expect, beforeEach, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { TooltipProvider } from "@/components/ui/tooltip"
import { RegistrationStatusIndicator } from "../registration-status"
import { useHeadsetStore } from "@/stores/headset-store"
import type { RegistrationStatus } from "@/lib/sip-client"

// Mock i18next (registration-status uses i18next.t directly, not useTranslation)
vi.mock("i18next", () => ({
  default: {
    t: (key: string) => {
      const translations: Record<string, string> = {
        "softphone.status.registered": "Registered",
        "softphone.status.connecting": "Connecting",
        "softphone.status.disconnected": "Disconnected",
        "softphone.status.error": "Error",
        "softphone.headset.connected": "Headset connected",
      }
      return translations[key] ?? key
    },
  },
}))

function Wrapper({ children }: { children: ReactNode }) {
  return <TooltipProvider>{children}</TooltipProvider>
}

function renderWithTooltip(ui: React.ReactElement) {
  return render(ui, { wrapper: Wrapper })
}

describe("RegistrationStatusIndicator", () => {
  beforeEach(() => {
    useHeadsetStore.getState().reset()
  })

  // ── Status text ────────────────────────────────────────────────────
  it("shows 'Registered' for registered status", () => {
    renderWithTooltip(<RegistrationStatusIndicator status="registered" />)
    expect(screen.getByText("Registered")).toBeInTheDocument()
  })

  it("shows 'Connecting' for connecting status", () => {
    renderWithTooltip(<RegistrationStatusIndicator status="connecting" />)
    expect(screen.getByText("Connecting")).toBeInTheDocument()
  })

  it("shows 'Disconnected' for disconnected status", () => {
    renderWithTooltip(<RegistrationStatusIndicator status="disconnected" />)
    expect(screen.getByText("Disconnected")).toBeInTheDocument()
  })

  it("shows 'Error' for error status", () => {
    renderWithTooltip(<RegistrationStatusIndicator status="error" />)
    expect(screen.getByText("Error")).toBeInTheDocument()
  })

  // ── Status dot colors ──────────────────────────────────────────────
  it("renders green dot for registered status", () => {
    const { container } = renderWithTooltip(
      <RegistrationStatusIndicator status="registered" />,
    )
    const dot = container.querySelector(".bg-green-500")
    expect(dot).toBeInTheDocument()
  })

  it("renders yellow dot for connecting status", () => {
    const { container } = renderWithTooltip(
      <RegistrationStatusIndicator status="connecting" />,
    )
    const dot = container.querySelector(".bg-yellow-500")
    expect(dot).toBeInTheDocument()
  })

  it("renders zinc/gray dot for disconnected status", () => {
    const { container } = renderWithTooltip(
      <RegistrationStatusIndicator status="disconnected" />,
    )
    const dot = container.querySelector(".bg-zinc-400")
    expect(dot).toBeInTheDocument()
  })

  it("renders red dot for error status", () => {
    const { container } = renderWithTooltip(
      <RegistrationStatusIndicator status="error" />,
    )
    const dot = container.querySelector(".bg-red-500")
    expect(dot).toBeInTheDocument()
  })

  // ── Headset indicator ──────────────────────────────────────────────
  it("does NOT show headset icon when no headset is connected", () => {
    useHeadsetStore.setState({ isConnected: false })
    const { container } = renderWithTooltip(
      <RegistrationStatusIndicator status="registered" />,
    )

    const svgs = container.querySelectorAll("svg")
    expect(svgs).toHaveLength(0)
  })

  it("shows headset icon when headset is connected", () => {
    useHeadsetStore.setState({
      isConnected: true,
      deviceName: "Jabra Evolve2",
      vendorName: "Jabra",
    })

    const { container } = renderWithTooltip(
      <RegistrationStatusIndicator status="registered" />,
    )

    const svgs = container.querySelectorAll("svg")
    expect(svgs.length).toBeGreaterThan(0)
  })

  // ── All four status types render without error ─────────────────────
  it.each<RegistrationStatus>(["registered", "connecting", "disconnected", "error"])(
    "renders without error for status=%s",
    (status) => {
      expect(() => {
        renderWithTooltip(<RegistrationStatusIndicator status={status} />)
      }).not.toThrow()
    },
  )
})
