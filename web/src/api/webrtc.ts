import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "./query-keys"

export interface WebRTCCredentials {
  sip_username: string
  sip_password: string
  sip_domain: string
  wss_url: string
  extension_number: string
  extension_id: string
  display_name: string
}

export function useWebRTCCredentials(enabled = true) {
  return useQuery({
    queryKey: queryKeys.webrtc.credentials(),
    queryFn: () => apiClient.get<WebRTCCredentials>("me/webrtc-credentials"),
    enabled,
    staleTime: 5 * 60 * 1000, // 5 min — credentials rarely change
    retry: false,
  })
}
