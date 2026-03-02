import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// Types matching backend RingGroupResponse
export interface RingGroup {
  id: string
  tenant_id: string
  group_number: string
  name: string
  ring_strategy: string
  ring_time: number
  ring_time_per_member: number
  skip_busy: boolean
  cid_passthrough: boolean
  confirm_calls: boolean
  failover_dest_type: string | null
  failover_dest_id: string | null
  moh_prompt_id: string | null
  member_extension_ids: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface RingGroupCreate {
  group_number: string
  name: string
  ring_strategy?: string
  ring_time?: number
  ring_time_per_member?: number
  skip_busy?: boolean
  cid_passthrough?: boolean
  confirm_calls?: boolean
  failover_dest_type?: string | null
  failover_dest_id?: string | null
  moh_prompt_id?: string | null
  member_extension_ids?: string[]
}

export function useRingGroups() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.ringGroups.list(tenantId),
    queryFn: () => apiClient.get<RingGroup[]>(`tenants/${tenantId}/ring-groups`),
    enabled: !!tenantId,
  })
}

export function useCreateRingGroup() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: RingGroupCreate) =>
      apiClient.post<RingGroup>(`tenants/${tenantId}/ring-groups`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.ringGroups.all(tenantId) }),
  })
}

export function useUpdateRingGroup() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<RingGroupCreate>) =>
      apiClient.patch<RingGroup>(`tenants/${tenantId}/ring-groups/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.ringGroups.all(tenantId) }),
  })
}

export function useDeleteRingGroup() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/ring-groups/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.ringGroups.all(tenantId) }),
  })
}
