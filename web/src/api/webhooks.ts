import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

export interface WebhookSubscription {
  id: string
  tenant_id: string
  name: string
  target_url: string
  event_types: string[]
  is_active: boolean
  description: string | null
  failure_count: number
  last_triggered_at: string | null
  created_at: string
  updated_at: string
}

export interface WebhookSubscriptionCreate {
  name: string
  target_url: string
  event_types: string[]
  description?: string | null
  is_active?: boolean
}

export interface WebhookSubscriptionUpdate {
  name?: string
  target_url?: string
  event_types?: string[]
  description?: string | null
  is_active?: boolean
}

export interface WebhookDeliveryLog {
  id: string
  subscription_id: string
  event_type: string
  payload: Record<string, unknown>
  status: string
  response_status_code: number | null
  response_body: string | null
  error_message: string | null
  attempt_count: number
  next_retry_at: string | null
  created_at: string
}

export function useWebhooks() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.webhooks.list(tenantId),
    queryFn: () => apiClient.get<WebhookSubscription[]>(`tenants/${tenantId}/webhooks`),
    enabled: !!tenantId,
  })
}

export function useCreateWebhook() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: WebhookSubscriptionCreate) =>
      apiClient.post<WebhookSubscription>(`tenants/${tenantId}/webhooks`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.webhooks.list(tenantId) }),
  })
}

export function useUpdateWebhook() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: WebhookSubscriptionUpdate }) =>
      apiClient.put<WebhookSubscription>(`tenants/${tenantId}/webhooks/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.webhooks.list(tenantId) }),
  })
}

export function useDeleteWebhook() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiClient.delete(`tenants/${tenantId}/webhooks/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.webhooks.list(tenantId) }),
  })
}

export function useWebhookDeliveries(webhookId: string, page: number = 1) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.webhooks.deliveries(tenantId, webhookId, page),
    queryFn: () =>
      apiClient.get<{ items: WebhookDeliveryLog[]; total: number; page: number; per_page: number }>(
        `tenants/${tenantId}/webhooks/${webhookId}/deliveries`,
        { page: String(page) }
      ),
    enabled: !!tenantId && !!webhookId,
  })
}

export function useTestWebhook() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (webhookId: string) =>
      apiClient.post<WebhookDeliveryLog>(`tenants/${tenantId}/webhooks/${webhookId}/test`, {
        event_type: "test.ping",
      }),
    onSuccess: (_, webhookId) =>
      qc.invalidateQueries({ queryKey: queryKeys.webhooks.deliveries(tenantId, webhookId) }),
  })
}
