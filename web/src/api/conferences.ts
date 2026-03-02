import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// Types matching backend ConferenceBridgeResponse
export interface ConferenceBridge {
  id: string
  tenant_id: string
  name: string
  room_number: string
  description: string | null
  max_participants: number
  participant_pin: string | null
  moderator_pin: string | null
  wait_for_moderator: boolean
  announce_join_leave: boolean
  record_conference: boolean
  muted_on_join: boolean
  moh_prompt_id: string | null
  enabled: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ConferenceBridgeCreate {
  name: string
  room_number: string
  description?: string | null
  max_participants?: number
  participant_pin?: string | null
  moderator_pin?: string | null
  wait_for_moderator?: boolean
  announce_join_leave?: boolean
  record_conference?: boolean
  muted_on_join?: boolean
  moh_prompt_id?: string | null
  enabled?: boolean
}

export function useConferences() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.conferences.list(tenantId),
    queryFn: () => apiClient.get<ConferenceBridge[]>(`tenants/${tenantId}/conferences`),
    enabled: !!tenantId,
  })
}

export function useCreateConference() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ConferenceBridgeCreate) =>
      apiClient.post<ConferenceBridge>(`tenants/${tenantId}/conferences`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.conferences.all(tenantId) }),
  })
}

export function useUpdateConference() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<ConferenceBridgeCreate>) =>
      apiClient.patch<ConferenceBridge>(`tenants/${tenantId}/conferences/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.conferences.all(tenantId) }),
  })
}

export function useDeleteConference() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/conferences/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.conferences.all(tenantId) }),
  })
}
