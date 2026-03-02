import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// Types matching backend FollowMeResponse
export interface FollowMeDestination {
  id: string
  position: number
  destination: string
  ring_time: number
}

export interface FollowMeDestinationData {
  destination: string
  ring_time?: number
}

export interface FollowMe {
  id: string
  tenant_id: string
  extension_id: string
  enabled: boolean
  strategy: string
  ring_extension_first: boolean
  extension_ring_time: number
  destinations: FollowMeDestination[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface FollowMeUpdate {
  enabled?: boolean
  strategy?: string
  ring_extension_first?: boolean
  extension_ring_time?: number
  destinations?: FollowMeDestinationData[]
}

export function useFollowMe(extensionId: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.followMe.detail(tenantId, extensionId),
    queryFn: () => apiClient.get<FollowMe>(`tenants/${tenantId}/extensions/${extensionId}/follow-me`),
    enabled: !!tenantId && !!extensionId,
  })
}

export function useUpdateFollowMe() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ extensionId, ...data }: { extensionId: string } & FollowMeUpdate) =>
      apiClient.put<FollowMe>(`tenants/${tenantId}/extensions/${extensionId}/follow-me`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.followMe.all(tenantId) }),
  })
}
