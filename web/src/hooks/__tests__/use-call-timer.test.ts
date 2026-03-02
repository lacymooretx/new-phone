import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { useCallTimer } from "../use-call-timer"

describe("useCallTimer", () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("returns empty string when startTime is null", () => {
    const { result } = renderHook(() => useCallTimer(null))
    expect(result.current).toBe("")
  })

  it("returns 00:00 immediately when timer starts", () => {
    const now = Date.now()
    vi.setSystemTime(now)

    const { result } = renderHook(() => useCallTimer(now))
    expect(result.current).toBe("00:00")
  })

  it("formats seconds correctly after 5 seconds", () => {
    const now = Date.now()
    vi.setSystemTime(now)

    const { result } = renderHook(() => useCallTimer(now))

    act(() => {
      vi.advanceTimersByTime(5000)
    })

    expect(result.current).toBe("00:05")
  })

  it("formats minutes correctly after 90 seconds", () => {
    const now = Date.now()
    vi.setSystemTime(now)

    const { result } = renderHook(() => useCallTimer(now))

    act(() => {
      vi.advanceTimersByTime(90_000)
    })

    expect(result.current).toBe("01:30")
  })

  it("formats double-digit minutes", () => {
    const now = Date.now()
    vi.setSystemTime(now)

    const { result } = renderHook(() => useCallTimer(now))

    act(() => {
      vi.advanceTimersByTime(605_000) // 10 minutes 5 seconds
    })

    expect(result.current).toBe("10:05")
  })

  it("resets to empty string when startTime becomes null", () => {
    const now = Date.now()
    vi.setSystemTime(now)

    const { result, rerender } = renderHook(
      ({ startTime }) => useCallTimer(startTime),
      { initialProps: { startTime: now as number | null } },
    )

    expect(result.current).toBe("00:00")

    // Advance a bit
    act(() => {
      vi.advanceTimersByTime(3000)
    })
    expect(result.current).toBe("00:03")

    // Stop the timer
    rerender({ startTime: null })
    expect(result.current).toBe("")
  })

  it("cleans up the interval on unmount", () => {
    const clearIntervalSpy = vi.spyOn(globalThis, "clearInterval")
    const now = Date.now()
    vi.setSystemTime(now)

    const { unmount } = renderHook(() => useCallTimer(now))
    unmount()

    expect(clearIntervalSpy).toHaveBeenCalled()
    clearIntervalSpy.mockRestore()
  })

  it("updates every second", () => {
    const now = Date.now()
    vi.setSystemTime(now)

    const { result } = renderHook(() => useCallTimer(now))

    // After 1 second
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(result.current).toBe("00:01")

    // After another second
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(result.current).toBe("00:02")

    // After another second
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(result.current).toBe("00:03")
  })
})
