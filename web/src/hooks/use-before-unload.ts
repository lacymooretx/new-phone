import { useEffect } from "react"

/**
 * Warns user before leaving the page when there are unsaved changes.
 */
export function useBeforeUnload(enabled: boolean) {
  useEffect(() => {
    if (!enabled) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
    }
    window.addEventListener("beforeunload", handler)
    return () => window.removeEventListener("beforeunload", handler)
  }, [enabled])
}
