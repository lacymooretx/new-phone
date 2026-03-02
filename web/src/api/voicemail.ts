import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

export interface VoicemailBox {
  id: string
  tenant_id: string
  mailbox_number: string
  greeting_type: string
  email_notification: boolean
  notification_email: string | null
  max_messages: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface VoicemailMessage {
  id: string
  tenant_id: string
  voicemail_box_id: string
  caller_number: string
  caller_name: string
  duration_seconds: number
  storage_path: string | null
  storage_bucket: string | null
  file_size_bytes: number
  format: string
  sha256_hash: string | null
  is_read: boolean
  is_urgent: boolean
  folder: string
  call_id: string | null
  email_sent: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface PlaybackResponse {
  url: string
  expires_in_seconds: number
}

export function useVoicemailBoxes() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.voicemail.boxes(tenantId),
    queryFn: () => apiClient.get<VoicemailBox[]>(`tenants/${tenantId}/voicemail-boxes`),
    enabled: !!tenantId,
  })
}

export function useVoicemailMessages(boxId: string | null) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.voicemail.messages(tenantId, boxId!),
    queryFn: () => apiClient.get<VoicemailMessage[]>(`tenants/${tenantId}/voicemail-boxes/${boxId}/messages`),
    enabled: !!tenantId && !!boxId,
  })
}

export function useVoicemailPlayback(boxId: string | null, messageId: string | null) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.voicemail.playback(tenantId, boxId!, messageId!),
    queryFn: () => apiClient.get<PlaybackResponse>(`tenants/${tenantId}/voicemail-boxes/${boxId}/messages/${messageId}/playback`),
    enabled: !!tenantId && !!boxId && !!messageId,
  })
}

export function useMarkMessageRead() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ boxId, messageId }: { boxId: string; messageId: string }) =>
      apiClient.patch(`tenants/${tenantId}/voicemail-boxes/${boxId}/messages/${messageId}`, { is_read: true }),
    onSuccess: (_, { boxId }) => qc.invalidateQueries({ queryKey: queryKeys.voicemail.messages(tenantId, boxId) }),
  })
}

export function useDeleteVoicemailMessage() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ boxId, messageId }: { boxId: string; messageId: string }) =>
      apiClient.delete(`tenants/${tenantId}/voicemail-boxes/${boxId}/messages/${messageId}`),
    onSuccess: (_, { boxId }) => qc.invalidateQueries({ queryKey: queryKeys.voicemail.messages(tenantId, boxId) }),
  })
}

// Voicemail Box CRUD

export interface VoicemailBoxCreate {
  mailbox_number: string
  pin: string
  greeting_type?: string
  email_notification?: boolean
  notification_email?: string | null
  max_messages?: number
}

export interface VoicemailBoxUpdate {
  mailbox_number?: string
  greeting_type?: string
  email_notification?: boolean
  notification_email?: string | null
  max_messages?: number
}

export interface PinResetResponse {
  pin: string
}

export function useCreateVoicemailBox() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: VoicemailBoxCreate) =>
      apiClient.post<VoicemailBox>(`tenants/${tenantId}/voicemail-boxes`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.voicemail.boxes(tenantId) }),
  })
}

export function useUpdateVoicemailBox() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & VoicemailBoxUpdate) =>
      apiClient.patch<VoicemailBox>(`tenants/${tenantId}/voicemail-boxes/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.voicemail.boxes(tenantId) }),
  })
}

export function useDeleteVoicemailBox() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/voicemail-boxes/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.voicemail.boxes(tenantId) }),
  })
}

export function useResetVoicemailPin() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useMutation({
    mutationFn: (boxId: string) =>
      apiClient.post<PinResetResponse>(`tenants/${tenantId}/voicemail-boxes/${boxId}/reset-pin`, {}),
  })
}
