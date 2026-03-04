import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

export interface ScheduledCallback {
  id: string
  tenant_id: string
  queue_id: string
  caller_number: string
  caller_name: string | null
  scheduled_at: string
  status: string
  queue_position: number | null
  attempt_count: number
  max_attempts: number
  completed_at: string | null
  agent_extension: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface ScheduledCallbackCreate {
  queue_id: string
  caller_number: string
  caller_name?: string | null
  scheduled_at: string
  max_attempts?: number
  notes?: string | null
}

export function useCallbacks(queueId?: string, status?: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.callbacks.list(tenantId, queueId, status),
    queryFn: () => {
      const params: Record<string, string> = {}
      if (queueId) params.queue_id = queueId
      if (status) params.status = status
      return apiClient.get<{ items: ScheduledCallback[]; total: number }>(`tenants/${tenantId}/callbacks`, params)
    },
    enabled: !!tenantId,
  })
}

export function useCreateCallback() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ScheduledCallbackCreate) =>
      apiClient.post<ScheduledCallback>(`tenants/${tenantId}/callbacks`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.callbacks.all(tenantId) }),
  })
}

export function useCancelCallback() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiClient.post(`tenants/${tenantId}/callbacks/${id}/cancel`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.callbacks.all(tenantId) }),
  })
}
