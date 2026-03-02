import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// ── Types ──────────────────────────────────────────────────────────

export interface SMSProviderConfig {
  id: string
  tenant_id: string
  provider_type: string
  label: string
  is_default: boolean
  is_active: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export interface SMSProviderConfigCreate {
  provider_type: "clearlyip" | "twilio"
  label: string
  credentials: Record<string, string>
  is_default?: boolean
  notes?: string | null
}

export interface Conversation {
  id: string
  tenant_id: string
  did_id: string
  remote_number: string
  channel: string
  state: string
  assigned_to_user_id: string | null
  queue_id: string | null
  last_message_at: string | null
  first_response_at: string | null
  resolved_at: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  did_number: string | null
  assigned_to_name: string | null
  queue_name: string | null
  unread_count: number
  last_message_preview: string | null
}

export interface ConversationMessage {
  id: string
  conversation_id: string
  direction: "inbound" | "outbound"
  from_number: string
  to_number: string
  body: string
  status: string
  provider: string | null
  provider_message_id: string | null
  sent_by_user_id: string | null
  error_message: string | null
  segments: number
  created_at: string
  sent_by_name: string | null
}

export interface ConversationNote {
  id: string
  conversation_id: string
  user_id: string
  body: string
  created_at: string
  user_name: string | null
}

// ── Conversations ──────────────────────────────────────────────────

export function useConversations(state?: string, queueId?: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.sms.conversations(tenantId, state, queueId),
    queryFn: () => {
      const params: Record<string, string> = {}
      if (state) params.state = state
      if (queueId) params.queue_id = queueId
      return apiClient.get<Conversation[]>(
        `tenants/${tenantId}/sms/conversations`,
        Object.keys(params).length > 0 ? params : undefined,
      )
    },
    enabled: !!tenantId,
  })
}

export function useConversation(conversationId: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.sms.conversationDetail(tenantId, conversationId),
    queryFn: () =>
      apiClient.get<Conversation>(`tenants/${tenantId}/sms/conversations/${conversationId}`),
    enabled: !!tenantId && !!conversationId,
  })
}

export function useConversationMessages(conversationId: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.sms.messages(tenantId, conversationId),
    queryFn: () =>
      apiClient.get<ConversationMessage[]>(
        `tenants/${tenantId}/sms/conversations/${conversationId}/messages`,
      ),
    enabled: !!tenantId && !!conversationId,
  })
}

export function useSendMessage() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ conversationId, body }: { conversationId: string; body: string }) =>
      apiClient.post<ConversationMessage>(
        `tenants/${tenantId}/sms/conversations/${conversationId}/messages`,
        { body },
      ),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: queryKeys.sms.messages(tenantId, variables.conversationId) })
      qc.invalidateQueries({ queryKey: queryKeys.sms.all(tenantId) })
    },
  })
}

export function useUpdateConversation() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      conversationId,
      ...data
    }: {
      conversationId: string
      state?: string
      assigned_to_user_id?: string | null
      queue_id?: string | null
    }) => apiClient.patch<Conversation>(`tenants/${tenantId}/sms/conversations/${conversationId}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.sms.all(tenantId) })
    },
  })
}

export function useClaimConversation() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (conversationId: string) =>
      apiClient.post<Conversation>(
        `tenants/${tenantId}/sms/conversations/${conversationId}/claim`,
        {},
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.sms.all(tenantId) })
    },
  })
}

export function useReleaseConversation() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (conversationId: string) =>
      apiClient.post<Conversation>(
        `tenants/${tenantId}/sms/conversations/${conversationId}/release`,
        {},
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.sms.all(tenantId) })
    },
  })
}

export function useReassignConversation() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ conversationId, userId }: { conversationId: string; userId: string }) =>
      apiClient.post<Conversation>(
        `tenants/${tenantId}/sms/conversations/${conversationId}/reassign`,
        { user_id: userId },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.sms.all(tenantId) })
    },
  })
}

// ── Notes ──────────────────────────────────────────────────────────

export function useConversationNotes(conversationId: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.sms.notes(tenantId, conversationId),
    queryFn: () =>
      apiClient.get<ConversationNote[]>(
        `tenants/${tenantId}/sms/conversations/${conversationId}/notes`,
      ),
    enabled: !!tenantId && !!conversationId,
  })
}

export function useCreateNote() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ conversationId, body }: { conversationId: string; body: string }) =>
      apiClient.post<ConversationNote>(
        `tenants/${tenantId}/sms/conversations/${conversationId}/notes`,
        { body },
      ),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: queryKeys.sms.notes(tenantId, variables.conversationId) })
    },
  })
}

// ── SMS Providers ──────────────────────────────────────────────────

export function useSMSProviders() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.sms.providers(tenantId),
    queryFn: () => apiClient.get<SMSProviderConfig[]>(`tenants/${tenantId}/sms/providers`),
    enabled: !!tenantId,
  })
}

export function useCreateSMSProvider() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: SMSProviderConfigCreate) =>
      apiClient.post<SMSProviderConfig>(`tenants/${tenantId}/sms/providers`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.sms.providers(tenantId) }),
  })
}

export function useUpdateSMSProvider() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<SMSProviderConfigCreate>) =>
      apiClient.patch<SMSProviderConfig>(`tenants/${tenantId}/sms/providers/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.sms.providers(tenantId) }),
  })
}

export function useDeleteSMSProvider() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/sms/providers/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.sms.providers(tenantId) }),
  })
}
