import { useEffect } from "react"
import { headsetManager } from "@/lib/headset-manager"
import { useSoftphoneStore } from "@/stores/softphone-store"

/**
 * Hook that bridges the headset manager with the softphone store.
 * Call once in softphone-panel.tsx — it handles init, state sync, and cleanup.
 */
export function useHeadset(): void {
  // Initialize headset manager on mount, destroy on unmount
  useEffect(() => {
    headsetManager.initialize()
    return () => headsetManager.destroy()
  }, [])

  // Subscribe to softphone state and forward changes to headset manager
  const callState = useSoftphoneStore((s) => s.callState)
  const isMuted = useSoftphoneStore((s) => s.isMuted)
  const isOnHold = useSoftphoneStore((s) => s.isOnHold)
  const remoteIdentity = useSoftphoneStore((s) => s.remoteIdentity)

  useEffect(() => {
    headsetManager.notifySoftphoneStateChange(callState, isMuted, isOnHold, remoteIdentity)
  }, [callState, isMuted, isOnHold, remoteIdentity])
}
