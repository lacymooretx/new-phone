import { describe, it, expect, beforeEach, vi } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"
import { useAudioDevices } from "../use-audio-devices"

const mockMicrophone: MediaDeviceInfo = {
  deviceId: "mic-001",
  groupId: "group-1",
  kind: "audioinput",
  label: "Built-in Microphone",
  toJSON: () => ({}),
}

const mockSpeaker: MediaDeviceInfo = {
  deviceId: "spk-001",
  groupId: "group-1",
  kind: "audiooutput",
  label: "Built-in Speakers",
  toJSON: () => ({}),
}

const mockWebcam: MediaDeviceInfo = {
  deviceId: "cam-001",
  groupId: "group-2",
  kind: "videoinput",
  label: "FaceTime HD Camera",
  toJSON: () => ({}),
}

const mockSecondMic: MediaDeviceInfo = {
  deviceId: "mic-002",
  groupId: "group-3",
  kind: "audioinput",
  label: "USB Headset Mic",
  toJSON: () => ({}),
}

describe("useAudioDevices", () => {
  let enumerateDevicesMock: ReturnType<typeof vi.fn>
  let addEventListenerMock: ReturnType<typeof vi.fn>
  let removeEventListenerMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    enumerateDevicesMock = vi.fn().mockResolvedValue([
      mockMicrophone,
      mockSpeaker,
      mockWebcam,
    ])
    addEventListenerMock = vi.fn()
    removeEventListenerMock = vi.fn()

    Object.defineProperty(navigator, "mediaDevices", {
      value: {
        enumerateDevices: enumerateDevicesMock,
        addEventListener: addEventListenerMock,
        removeEventListener: removeEventListenerMock,
      },
      writable: true,
      configurable: true,
    })
  })

  it("enumerates devices on mount", async () => {
    const { result } = renderHook(() => useAudioDevices())

    await waitFor(() => {
      expect(result.current.microphones).toHaveLength(1)
    })

    expect(enumerateDevicesMock).toHaveBeenCalled()
  })

  it("filters to only audio input and output devices", async () => {
    const { result } = renderHook(() => useAudioDevices())

    await waitFor(() => {
      expect(result.current.microphones).toHaveLength(1)
    })

    // Should not include the webcam
    expect(result.current.microphones[0].label).toBe("Built-in Microphone")
    expect(result.current.speakers[0].label).toBe("Built-in Speakers")
  })

  it("separates microphones and speakers", async () => {
    enumerateDevicesMock.mockResolvedValue([
      mockMicrophone,
      mockSecondMic,
      mockSpeaker,
    ])

    const { result } = renderHook(() => useAudioDevices())

    await waitFor(() => {
      expect(result.current.microphones).toHaveLength(2)
    })

    expect(result.current.speakers).toHaveLength(1)
  })

  it("selects first mic and speaker as defaults", async () => {
    const { result } = renderHook(() => useAudioDevices())

    await waitFor(() => {
      expect(result.current.selectedMic).toBe("mic-001")
    })

    expect(result.current.selectedSpeaker).toBe("spk-001")
  })

  it("registers devicechange listener on mount", async () => {
    renderHook(() => useAudioDevices())

    await waitFor(() => {
      expect(addEventListenerMock).toHaveBeenCalledWith(
        "devicechange",
        expect.any(Function),
      )
    })
  })

  it("removes devicechange listener on unmount", async () => {
    const { unmount } = renderHook(() => useAudioDevices())

    await waitFor(() => {
      expect(addEventListenerMock).toHaveBeenCalled()
    })

    unmount()

    expect(removeEventListenerMock).toHaveBeenCalledWith(
      "devicechange",
      expect.any(Function),
    )
  })

  it("allows changing selected microphone", async () => {
    enumerateDevicesMock.mockResolvedValue([
      mockMicrophone,
      mockSecondMic,
      mockSpeaker,
    ])

    const { result } = renderHook(() => useAudioDevices())

    await waitFor(() => {
      expect(result.current.selectedMic).toBe("mic-001")
    })

    act(() => {
      result.current.setSelectedMic("mic-002")
    })

    expect(result.current.selectedMic).toBe("mic-002")
  })

  it("allows changing selected speaker", async () => {
    const { result } = renderHook(() => useAudioDevices())

    await waitFor(() => {
      expect(result.current.selectedSpeaker).toBe("spk-001")
    })

    act(() => {
      result.current.setSelectedSpeaker("spk-external")
    })

    expect(result.current.selectedSpeaker).toBe("spk-external")
  })

  it("handles permission denied gracefully", async () => {
    enumerateDevicesMock.mockRejectedValue(new DOMException("Permission denied"))

    const { result } = renderHook(() => useAudioDevices())

    // Should still work without crashing, devices remain empty
    await waitFor(() => {
      expect(enumerateDevicesMock).toHaveBeenCalled()
    })

    expect(result.current.microphones).toHaveLength(0)
    expect(result.current.speakers).toHaveLength(0)
  })

  it("generates fallback labels for devices without labels", async () => {
    enumerateDevicesMock.mockResolvedValue([
      {
        deviceId: "no-label-mic",
        groupId: "g1",
        kind: "audioinput",
        label: "",
        toJSON: () => ({}),
      },
    ])

    const { result } = renderHook(() => useAudioDevices())

    await waitFor(() => {
      expect(result.current.microphones).toHaveLength(1)
    })

    // Should generate a fallback label containing "Microphone"
    expect(result.current.microphones[0].label).toContain("Microphone")
  })
})
