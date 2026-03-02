import { describe, it, expect, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import { useBeforeUnload } from "../use-before-unload"

describe("useBeforeUnload", () => {
  it("registers beforeunload listener when enabled=true", () => {
    const addSpy = vi.spyOn(window, "addEventListener")

    renderHook(() => useBeforeUnload(true))

    const calls = addSpy.mock.calls.filter(([e]) => e === "beforeunload")
    expect(calls).toHaveLength(1)

    addSpy.mockRestore()
  })

  it("does NOT register listener when enabled=false", () => {
    const addSpy = vi.spyOn(window, "addEventListener")

    renderHook(() => useBeforeUnload(false))

    const calls = addSpy.mock.calls.filter(([e]) => e === "beforeunload")
    expect(calls).toHaveLength(0)

    addSpy.mockRestore()
  })

  it("removes listener on unmount when enabled=true", () => {
    const removeSpy = vi.spyOn(window, "removeEventListener")

    const { unmount } = renderHook(() => useBeforeUnload(true))
    unmount()

    const calls = removeSpy.mock.calls.filter(([e]) => e === "beforeunload")
    expect(calls).toHaveLength(1)

    removeSpy.mockRestore()
  })

  it("handler calls preventDefault on the event", () => {
    const addSpy = vi.spyOn(window, "addEventListener")

    renderHook(() => useBeforeUnload(true))

    const handler = addSpy.mock.calls.find(
      ([event]) => event === "beforeunload",
    )?.[1] as EventListener

    expect(handler).toBeDefined()

    const event = new Event("beforeunload")
    const preventDefaultSpy = vi.spyOn(event, "preventDefault")
    handler(event)
    expect(preventDefaultSpy).toHaveBeenCalled()

    addSpy.mockRestore()
  })

  it("removes old listener and re-adds when enabled changes from true to false", () => {
    const removeSpy = vi.spyOn(window, "removeEventListener")

    const { rerender } = renderHook(
      ({ enabled }) => useBeforeUnload(enabled),
      { initialProps: { enabled: true } },
    )

    rerender({ enabled: false })

    const calls = removeSpy.mock.calls.filter(([e]) => e === "beforeunload")
    expect(calls.length).toBeGreaterThanOrEqual(1)

    removeSpy.mockRestore()
  })

  it("does not remove beforeunload listener on unmount when enabled=false", () => {
    const removeSpy = vi.spyOn(window, "removeEventListener")

    const { unmount } = renderHook(() => useBeforeUnload(false))
    unmount()

    const calls = removeSpy.mock.calls.filter(([e]) => e === "beforeunload")
    expect(calls).toHaveLength(0)

    removeSpy.mockRestore()
  })
})
