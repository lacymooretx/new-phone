import { useEffect, useRef } from "react"
import { useAuthStore } from "@/stores/auth-store"
import { useSoftphoneStore } from "@/stores/softphone-store"
import { useWebRTCCredentials } from "@/api/webrtc"

export function useSoftphoneInit(remoteAudioRef: React.RefObject<HTMLAudioElement | null>) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const { connect, disconnect, status } = useSoftphoneStore()
  const { data: credentials } = useWebRTCCredentials(isAuthenticated)
  const connectedRef = useRef(false)

  useEffect(() => {
    if (!isAuthenticated) {
      if (connectedRef.current) {
        disconnect()
        connectedRef.current = false
      }
      return
    }

    if (!credentials || !remoteAudioRef.current) return
    if (connectedRef.current) return

    connectedRef.current = true
    connect(
      {
        wssUrl: credentials.wss_url,
        sipUsername: credentials.sip_username,
        sipPassword: credentials.sip_password,
        sipDomain: credentials.sip_domain,
        displayName: credentials.display_name,
      },
      remoteAudioRef.current
    ).catch(() => {
      connectedRef.current = false
    })
  }, [isAuthenticated, credentials, remoteAudioRef, connect, disconnect])

  // Disconnect on unmount
  useEffect(() => {
    return () => {
      if (connectedRef.current) {
        disconnect()
        connectedRef.current = false
      }
    }
  }, [disconnect])

  return { status }
}
