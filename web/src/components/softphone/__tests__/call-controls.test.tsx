import type { ReactNode } from "react"
import { describe, it, expect, beforeEach, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { TooltipProvider } from "@/components/ui/tooltip"
import { CallControls } from "../call-controls"
import { useSoftphoneStore } from "@/stores/softphone-store"

// Radix tooltip popper needs ResizeObserver
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        "softphone.mute": "Mute",
        "softphone.unmute": "Unmute",
        "softphone.hold": "Hold",
        "softphone.resume": "Resume",
        "softphone.park": "Park",
        "softphone.hangUp": "Hang up",
      }
      return translations[key] ?? key
    },
    i18n: { language: "en" },
  }),
}))

// Mock the sip-client and desktop-bridge so the store module loads cleanly
vi.mock("@/lib/sip-client", () => ({
  SipClient: class {},
}))
vi.mock("@/lib/desktop-bridge", () => ({
  isDesktop: vi.fn().mockReturnValue(false),
  showNativeNotification: vi.fn(),
}))

function Wrapper({ children }: { children: ReactNode }) {
  return <TooltipProvider>{children}</TooltipProvider>
}

function renderWithTooltip(ui: React.ReactElement) {
  return render(ui, { wrapper: Wrapper })
}

describe("CallControls", () => {
  const mockToggleMute = vi.fn()
  const mockToggleHold = vi.fn().mockResolvedValue(undefined)
  const mockHangup = vi.fn().mockResolvedValue(undefined)
  const mockSendDTMF = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()

    // Use real Zustand store, set state directly
    useSoftphoneStore.setState({
      isMuted: false,
      isOnHold: false,
      callState: "connected",
    })

    // Patch the action methods by overwriting them on the store
    useSoftphoneStore.setState({
      toggleMute: mockToggleMute,
      toggleHold: mockToggleHold,
      hangup: mockHangup,
      sendDTMF: mockSendDTMF,
    })
  })

  // ── Rendering ──────────────────────────────────────────────────────
  it("renders mute, hold, park, and hangup buttons when connected", () => {
    renderWithTooltip(<CallControls />)
    expect(screen.getAllByRole("button")).toHaveLength(4)
  })

  it("renders 3 buttons when call is on_hold (no park)", () => {
    useSoftphoneStore.setState({ callState: "on_hold" })
    renderWithTooltip(<CallControls />)
    expect(screen.getAllByRole("button")).toHaveLength(3)
  })

  // ── Mute toggle ────────────────────────────────────────────────────
  it("calls toggleMute when mute button is clicked", async () => {
    const user = userEvent.setup()
    renderWithTooltip(<CallControls />)

    const buttons = screen.getAllByRole("button")
    await user.click(buttons[0])

    expect(mockToggleMute).toHaveBeenCalledOnce()
  })

  it("shows destructive variant for mute button when muted", () => {
    useSoftphoneStore.setState({ isMuted: true })
    renderWithTooltip(<CallControls />)

    const muteButton = screen.getAllByRole("button")[0]
    expect(muteButton.className).toMatch(/destructive/)
  })

  it("shows outline variant for mute button when not muted", () => {
    useSoftphoneStore.setState({ isMuted: false })
    renderWithTooltip(<CallControls />)

    const muteButton = screen.getAllByRole("button")[0]
    // The outline variant uses bg-background; destructive variant uses bg-destructive
    // Use a word-boundary check to avoid matching "aria-invalid:ring-destructive"
    expect(muteButton.className).toMatch(/\bbg-background\b/)
    expect(muteButton.className).not.toMatch(/\bbg-destructive\b/)
  })

  // ── Hold toggle ────────────────────────────────────────────────────
  it("calls toggleHold when hold button is clicked", async () => {
    const user = userEvent.setup()
    renderWithTooltip(<CallControls />)

    const buttons = screen.getAllByRole("button")
    await user.click(buttons[1])

    expect(mockToggleHold).toHaveBeenCalledOnce()
  })

  // ── Park button ────────────────────────────────────────────────────
  it("shows park button only when callState is connected", () => {
    useSoftphoneStore.setState({ callState: "connected" })
    renderWithTooltip(<CallControls />)
    expect(screen.getAllByRole("button")).toHaveLength(4)
  })

  it("hides park button when call is on hold", () => {
    useSoftphoneStore.setState({ callState: "on_hold" })
    renderWithTooltip(<CallControls />)
    expect(screen.getAllByRole("button")).toHaveLength(3)
  })

  it("sends *85 DTMF when park button is clicked", async () => {
    const user = userEvent.setup()
    useSoftphoneStore.setState({ callState: "connected" })
    renderWithTooltip(<CallControls />)

    // Park is the 3rd button (index 2) when connected
    const buttons = screen.getAllByRole("button")
    await user.click(buttons[2])

    expect(mockSendDTMF).toHaveBeenCalledWith("*85")
  })

  // ── Hangup button ──────────────────────────────────────────────────
  it("calls hangup when hangup button is clicked", async () => {
    const user = userEvent.setup()
    renderWithTooltip(<CallControls />)

    const buttons = screen.getAllByRole("button")
    await user.click(buttons[buttons.length - 1])

    expect(mockHangup).toHaveBeenCalledOnce()
  })

  it("hangup button has destructive variant", () => {
    renderWithTooltip(<CallControls />)

    const buttons = screen.getAllByRole("button")
    const hangupButton = buttons[buttons.length - 1]
    expect(hangupButton.className).toMatch(/destructive/)
  })

  // ── Ringing states ─────────────────────────────────────────────────
  it("hides park button during ringing_out", () => {
    useSoftphoneStore.setState({ callState: "ringing_out" })
    renderWithTooltip(<CallControls />)
    expect(screen.getAllByRole("button")).toHaveLength(3)
  })
})
