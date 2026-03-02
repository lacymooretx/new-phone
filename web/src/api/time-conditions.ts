import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// Types matching backend TimeConditionRule / TimeConditionResponse
export interface TimeConditionRule {
  type: string
  days?: number[] | null
  start_time?: string | null
  end_time?: string | null
  start_date?: string | null
  end_date?: string | null
  invert?: boolean
  label?: string | null
}

export interface TimeCondition {
  id: string
  tenant_id: string
  name: string
  description: string | null
  timezone: string
  rules: TimeConditionRule[]
  match_destination_type: string
  match_destination_id: string | null
  nomatch_destination_type: string
  nomatch_destination_id: string | null
  holiday_calendar_id: string | null
  manual_override: string | null
  site_id: string | null
  enabled: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface TimeConditionCreate {
  name: string
  description?: string | null
  timezone?: string
  rules?: TimeConditionRule[]
  match_destination_type: string
  match_destination_id?: string | null
  nomatch_destination_type: string
  nomatch_destination_id?: string | null
  holiday_calendar_id?: string | null
  enabled?: boolean
  site_id?: string | null
}

export function useTimeConditions() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.timeConditions.list(tenantId),
    queryFn: () => apiClient.get<TimeCondition[]>(`tenants/${tenantId}/time-conditions`),
    enabled: !!tenantId,
  })
}

export function useCreateTimeCondition() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TimeConditionCreate) =>
      apiClient.post<TimeCondition>(`tenants/${tenantId}/time-conditions`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.timeConditions.all(tenantId) }),
  })
}

export function useUpdateTimeCondition() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<TimeConditionCreate>) =>
      apiClient.patch<TimeCondition>(`tenants/${tenantId}/time-conditions/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.timeConditions.all(tenantId) }),
  })
}

export function useDeleteTimeCondition() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/time-conditions/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.timeConditions.all(tenantId) }),
  })
}
