import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// Types matching backend QueueResponse
export interface QueueMember {
  id: string
  queue_id: string
  extension_id: string
  level: number
  position: number
}

export interface Queue {
  id: string
  tenant_id: string
  name: string
  queue_number: string
  description: string | null
  strategy: string
  moh_prompt_id: string | null
  max_wait_time: number
  max_wait_time_with_no_agent: number
  tier_rules_apply: boolean
  tier_rule_wait_second: number
  tier_rule_wait_multiply_level: boolean
  tier_rule_no_agent_no_wait: boolean
  discard_abandoned_after: number
  abandoned_resume_allowed: boolean
  caller_exit_key: string | null
  wrapup_time: number
  ring_timeout: number
  announce_frequency: number
  announce_prompt_id: string | null
  overflow_destination_type: string | null
  overflow_destination_id: string | null
  record_calls: boolean
  enabled: boolean
  disposition_required: boolean
  disposition_code_list_id: string | null
  members: QueueMember[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface QueueMemberCreate {
  extension_id: string
  level?: number
  position?: number
}

export interface QueueCreate {
  name: string
  queue_number: string
  description?: string | null
  strategy?: string
  moh_prompt_id?: string | null
  max_wait_time?: number
  max_wait_time_with_no_agent?: number
  tier_rules_apply?: boolean
  tier_rule_wait_second?: number
  tier_rule_wait_multiply_level?: boolean
  tier_rule_no_agent_no_wait?: boolean
  discard_abandoned_after?: number
  abandoned_resume_allowed?: boolean
  caller_exit_key?: string | null
  wrapup_time?: number
  ring_timeout?: number
  announce_frequency?: number
  announce_prompt_id?: string | null
  overflow_destination_type?: string | null
  overflow_destination_id?: string | null
  record_calls?: boolean
  enabled?: boolean
  disposition_required?: boolean
  disposition_code_list_id?: string | null
  members?: QueueMemberCreate[]
}

export function useQueues() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.queues.list(tenantId),
    queryFn: () => apiClient.get<Queue[]>(`tenants/${tenantId}/queues`),
    enabled: !!tenantId,
  })
}

export function useCreateQueue() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: QueueCreate) =>
      apiClient.post<Queue>(`tenants/${tenantId}/queues`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.queues.all(tenantId) }),
  })
}

export function useUpdateQueue() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<QueueCreate>) =>
      apiClient.patch<Queue>(`tenants/${tenantId}/queues/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.queues.all(tenantId) }),
  })
}

export function useDeleteQueue() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/queues/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.queues.all(tenantId) }),
  })
}

// Queue stats types
export interface QueueStats {
  queue_id: string
  queue_name: string
  waiting_count: number
  agents_logged_in: number
  agents_available: number
  agents_on_call: number
  longest_wait_seconds: number
}

export interface AgentStatus {
  extension_id: string
  extension_number: string
  agent_status: string | null
}

export function useQueueStats() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.queues.stats(tenantId),
    queryFn: () => apiClient.get<QueueStats[]>(`tenants/${tenantId}/queues/stats`),
    enabled: !!tenantId,
    refetchInterval: 30_000,
  })
}

export function useQueueStatsById(queueId: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: [...queryKeys.queues.stats(tenantId), queueId],
    queryFn: () => apiClient.get<QueueStats>(`tenants/${tenantId}/queues/${queueId}/stats`),
    enabled: !!tenantId && !!queueId,
    refetchInterval: 30_000,
  })
}

export function useAgentStatus() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.queues.agentStatus(tenantId),
    queryFn: () => apiClient.get<AgentStatus[]>(`tenants/${tenantId}/queues/agent-status`),
    enabled: !!tenantId,
    refetchInterval: 30_000,
  })
}
