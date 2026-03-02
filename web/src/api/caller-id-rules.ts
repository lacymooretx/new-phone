import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// Types matching backend CallerIdRuleResponse
export interface CallerIdRule {
  id: string
  tenant_id: string
  name: string
  rule_type: string
  match_pattern: string
  action: string
  priority: number
  notes: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CallerIdRuleCreate {
  name: string
  rule_type: string
  match_pattern: string
  action: string
  priority?: number
  notes?: string | null
}

export function useCallerIdRules() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.callerIdRules.list(tenantId),
    queryFn: () => apiClient.get<CallerIdRule[]>(`tenants/${tenantId}/caller-id-rules`),
    enabled: !!tenantId,
  })
}

export function useCreateCallerIdRule() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CallerIdRuleCreate) =>
      apiClient.post<CallerIdRule>(`tenants/${tenantId}/caller-id-rules`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.callerIdRules.all(tenantId) }),
  })
}

export function useUpdateCallerIdRule() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<CallerIdRuleCreate>) =>
      apiClient.patch<CallerIdRule>(`tenants/${tenantId}/caller-id-rules/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.callerIdRules.all(tenantId) }),
  })
}

export function useDeleteCallerIdRule() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/caller-id-rules/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.callerIdRules.all(tenantId) }),
  })
}
