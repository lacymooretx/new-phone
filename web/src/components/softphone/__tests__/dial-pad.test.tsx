import { describe, it, expect, beforeEach, vi } from "vitest"
import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { renderWithProviders } from "@/test/render"
import { DialPad } from "../dial-pad"
import { useSoftphoneStore } from "@/stores/softphone-store"

// Mock react-i18next to return translation keys as values
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        "softphone.enterNumber": "Enter number",
        "softphone.call": "Call",
      }
      return translations[key] ?? key
    },
    i18n: { language: "en" },
  }),
}))

// Mock the softphone store
const mockMakeCall = vi.fn().mockResolvedValue(undefined)
const mockSendDTMF = vi.fn()

vi.mock("@/stores/softphone-store", () => ({
  useSoftphoneStore: vi.fn(),
}))

const mockedUseSoftphoneStore = vi.mocked(useSoftphoneStore)

describe("DialPad", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedUseSoftphoneStore.mockReturnValue({
      callState: "idle",
      makeCall: mockMakeCall,
      sendDTMF: mockSendDTMF,
    } as ReturnType<typeof useSoftphoneStore>)
  })

  it("renders all 12 dial pad buttons", () => {
    renderWithProviders(<DialPad />)

    const expectedKeys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#"]
    for (const key of expectedKeys) {
      expect(screen.getByRole("button", { name: key })).toBeInTheDocument()
    }
  })

  it("renders the number input field", () => {
    renderWithProviders(<DialPad />)

    expect(screen.getByPlaceholderText("Enter number")).toBeInTheDocument()
  })

  it("renders the call button when not in a call", () => {
    renderWithProviders(<DialPad />)

    expect(screen.getByRole("button", { name: /call/i })).toBeInTheDocument()
  })

  it("appends digit to input when key is clicked", async () => {
    const user = userEvent.setup()
    renderWithProviders(<DialPad />)

    await user.click(screen.getByRole("button", { name: "1" }))
    await user.click(screen.getByRole("button", { name: "2" }))
    await user.click(screen.getByRole("button", { name: "3" }))

    expect(screen.getByPlaceholderText("Enter number")).toHaveValue("123")
  })

  it("does NOT send DTMF when idle (not in call)", async () => {
    const user = userEvent.setup()
    renderWithProviders(<DialPad />)

    await user.click(screen.getByRole("button", { name: "5" }))

    expect(mockSendDTMF).not.toHaveBeenCalled()
  })

  it("sends DTMF when in a connected call", async () => {
    mockedUseSoftphoneStore.mockReturnValue({
      callState: "connected",
      makeCall: mockMakeCall,
      sendDTMF: mockSendDTMF,
    } as ReturnType<typeof useSoftphoneStore>)

    const user = userEvent.setup()
    renderWithProviders(<DialPad />)

    await user.click(screen.getByRole("button", { name: "9" }))

    expect(mockSendDTMF).toHaveBeenCalledWith("9")
  })

  it("sends DTMF when call is on hold", async () => {
    mockedUseSoftphoneStore.mockReturnValue({
      callState: "on_hold",
      makeCall: mockMakeCall,
      sendDTMF: mockSendDTMF,
    } as ReturnType<typeof useSoftphoneStore>)

    const user = userEvent.setup()
    renderWithProviders(<DialPad />)

    await user.click(screen.getByRole("button", { name: "*" }))

    expect(mockSendDTMF).toHaveBeenCalledWith("*")
  })

  it("calls makeCall with the entered number on call button click", async () => {
    const user = userEvent.setup()
    renderWithProviders(<DialPad />)

    const input = screen.getByPlaceholderText("Enter number")
    await user.type(input, "1001")
    await user.click(screen.getByRole("button", { name: /call/i }))

    expect(mockMakeCall).toHaveBeenCalledWith("1001")
  })

  it("clears input after making a call", async () => {
    const user = userEvent.setup()
    renderWithProviders(<DialPad />)

    const input = screen.getByPlaceholderText("Enter number")
    await user.type(input, "2002")
    await user.click(screen.getByRole("button", { name: /call/i }))

    expect(input).toHaveValue("")
  })

  it("disables call button when input is empty", () => {
    renderWithProviders(<DialPad />)

    const callButton = screen.getByRole("button", { name: /call/i })
    expect(callButton).toBeDisabled()
  })

  it("disables call button when callState is not idle", async () => {
    mockedUseSoftphoneStore.mockReturnValue({
      callState: "ringing_out",
      makeCall: mockMakeCall,
      sendDTMF: mockSendDTMF,
    } as ReturnType<typeof useSoftphoneStore>)

    const user = userEvent.setup()
    renderWithProviders(<DialPad />)

    // Type a number so the empty check passes
    await user.type(screen.getByPlaceholderText("Enter number"), "100")

    const callButton = screen.getByRole("button", { name: /call/i })
    expect(callButton).toBeDisabled()
  })

  it("hides call button when in a connected call", () => {
    mockedUseSoftphoneStore.mockReturnValue({
      callState: "connected",
      makeCall: mockMakeCall,
      sendDTMF: mockSendDTMF,
    } as ReturnType<typeof useSoftphoneStore>)

    renderWithProviders(<DialPad />)

    expect(screen.queryByRole("button", { name: /call/i })).not.toBeInTheDocument()
  })

  it("makes a call on Enter key in the input", async () => {
    const user = userEvent.setup()
    renderWithProviders(<DialPad />)

    const input = screen.getByPlaceholderText("Enter number")
    await user.type(input, "3003")
    await user.keyboard("{Enter}")

    expect(mockMakeCall).toHaveBeenCalledWith("3003")
  })

  it("does not make a call on Enter if input is empty", async () => {
    const user = userEvent.setup()
    renderWithProviders(<DialPad />)

    const input = screen.getByPlaceholderText("Enter number")
    await user.click(input)
    await user.keyboard("{Enter}")

    expect(mockMakeCall).not.toHaveBeenCalled()
  })
})
