import { useState, useEffect, useRef } from "react"

export function useCallTimer(startTime: number | null): string {
  const [elapsed, setElapsed] = useState("")
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }

    if (!startTime) {
      setElapsed("")
      return
    }

    const update = () => {
      const diff = Math.floor((Date.now() - startTime) / 1000)
      const mins = Math.floor(diff / 60)
      const secs = diff % 60
      setElapsed(`${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`)
    }

    update()
    intervalRef.current = setInterval(update, 1000)
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [startTime])

  return elapsed
}
