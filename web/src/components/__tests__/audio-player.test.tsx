import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { AudioPlayer } from "@/components/shared/audio-player"

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe("AudioPlayer", () => {
  const mockFetchUrl = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    // Mock HTMLMediaElement.play and pause
    HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue(undefined)
    HTMLMediaElement.prototype.pause = vi.fn()
  })

  it("renders a play button", () => {
    render(<AudioPlayer fetchUrl={mockFetchUrl} />)
    expect(screen.getByRole("button")).toBeInTheDocument()
  })

  it("calls fetchUrl when play button is clicked for the first time", async () => {
    const user = userEvent.setup()
    mockFetchUrl.mockResolvedValue({ url: "https://example.com/audio.mp3" })

    render(<AudioPlayer fetchUrl={mockFetchUrl} />)
    await user.click(screen.getByRole("button"))

    expect(mockFetchUrl).toHaveBeenCalledTimes(1)
  })

  it("does not render audio element before URL is fetched", () => {
    const { container } = render(<AudioPlayer fetchUrl={mockFetchUrl} />)
    expect(container.querySelector("audio")).not.toBeInTheDocument()
  })

  it("renders audio element after URL is fetched", async () => {
    const user = userEvent.setup()
    mockFetchUrl.mockResolvedValue({ url: "https://example.com/audio.mp3" })

    const { container } = render(<AudioPlayer fetchUrl={mockFetchUrl} />)
    await user.click(screen.getByRole("button"))

    await waitFor(() => {
      expect(container.querySelector("audio")).toBeInTheDocument()
    })
  })

  it("shows error toast when fetchUrl fails", async () => {
    const user = userEvent.setup()
    const { toast } = await import("sonner")
    mockFetchUrl.mockRejectedValue(new Error("Network error"))

    render(<AudioPlayer fetchUrl={mockFetchUrl} />)
    await user.click(screen.getByRole("button"))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Failed to load audio")
    })
  })
})
