import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

export interface BossAdminRelationship {
  id: string
  tenant_id: string
  executive_extension_id: string
  assistant_extension_id: string
  filter_mode: string
  overflow_ring_time: number
  dnd_override_enabled: boolean
  vip_caller_ids: string[]
  is_active: boolean
  created_at: string
  updated_at: string
  executive_extension_number: string | null
  assistant_extension_number: string | null
}

export interface BossAdminCreate {
  executive_extension_id: string
  assistant_extension_id: string
  filter_mode?: string
  overflow_ring_time?: number
  dnd_override_enabled?: boolean
  vip_caller_ids?: string[]
}

export interface BossAdminUpdate {
  filter_mode?: string
  overflow_ring_time?: number
  dnd_override_enabled?: boolean
  vip_caller_ids?: string[]
  is_active?: boolean
}

export const FILTER_MODES = [
  { value: "all_to_assistant", labelKey: "bossAdmin.filterModes.allToAssistant" },
  { value: "simultaneous_ring", labelKey: "bossAdmin.filterModes.simultaneousRing" },
  { value: "assistant_overflow", labelKey: "bossAdmin.filterModes.assistantOverflow" },
  { value: "screening", labelKey: "bossAdmin.filterModes.screening" },
  { value: "vip_bypass", labelKey: "bossAdmin.filterModes.vipBypass" },
  { value: "dnd_override", labelKey: "bossAdmin.filterModes.dndOverride" },
] as const

export function useBossAdminRelationships(filters?: {
  executive_id?: string
  assistant_id?: string
}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const params = new URLSearchParams()
  if (filters?.executive_id) params.set("executive_id", filters.executive_id)
  if (filters?.assistant_id) params.set("assistant_id", filters.assistant_id)
  const qs = params.toString()
  return useQuery({
    queryKey: queryKeys.bossAdmin.relationships(tenantId),
    queryFn: () =>
      apiClient.get<BossAdminRelationship[]>(
        `tenants/${tenantId}/boss-admin/relationships${qs ? `?${qs}` : ""}`
      ),
    enabled: !!tenantId,
  })
}

export function useCreateBossAdminRelationship() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: BossAdminCreate) =>
      apiClient.post<BossAdminRelationship>(
        `tenants/${tenantId}/boss-admin/relationships`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.bossAdmin.all(tenantId) }),
  })
}

export function useUpdateBossAdminRelationship() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & BossAdminUpdate) =>
      apiClient.patch<BossAdminRelationship>(
        `tenants/${tenantId}/boss-admin/relationships/${id}`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.bossAdmin.all(tenantId) }),
  })
}

export function useDeleteBossAdminRelationship() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/boss-admin/relationships/${id}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.bossAdmin.all(tenantId) }),
  })
}

export function useMyExecutives() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.bossAdmin.myExecutives(tenantId),
    queryFn: () =>
      apiClient.get<BossAdminRelationship[]>(
        `tenants/${tenantId}/boss-admin/my-executives`
      ),
    enabled: !!tenantId,
  })
}

export function useMyAssistants() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.bossAdmin.myAssistants(tenantId),
    queryFn: () =>
      apiClient.get<BossAdminRelationship[]>(
        `tenants/${tenantId}/boss-admin/my-assistants`
      ),
    enabled: !!tenantId,
  })
}
