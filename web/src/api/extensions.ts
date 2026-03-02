import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// Types matching backend ExtensionResponse
export interface Extension {
  id: string
  tenant_id: string
  extension_number: string
  sip_username: string
  user_id: string | null
  voicemail_box_id: string | null
  internal_cid_name: string | null
  internal_cid_number: string | null
  external_cid_name: string | null
  external_cid_number: string | null
  emergency_cid_number: string | null
  e911_street: string | null
  e911_city: string | null
  e911_state: string | null
  e911_zip: string | null
  e911_country: string | null
  call_forward_unconditional: string | null
  call_forward_busy: string | null
  call_forward_no_answer: string | null
  call_forward_not_registered: string | null
  call_forward_ring_time: number
  dnd_enabled: boolean
  call_waiting: boolean
  max_registrations: number
  outbound_cid_mode: string
  class_of_service: string
  recording_policy: string
  notes: string | null
  agent_status: string | null
  pickup_group: string | null
  site_id: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ExtensionCreate {
  extension_number: string
  user_id?: string | null
  voicemail_box_id?: string | null
  internal_cid_name?: string | null
  internal_cid_number?: string | null
  external_cid_name?: string | null
  external_cid_number?: string | null
  emergency_cid_number?: string | null
  e911_street?: string | null
  e911_city?: string | null
  e911_state?: string | null
  e911_zip?: string | null
  e911_country?: string | null
  call_forward_unconditional?: string | null
  call_forward_busy?: string | null
  call_forward_no_answer?: string | null
  call_forward_not_registered?: string | null
  call_forward_ring_time?: number
  dnd_enabled?: boolean
  call_waiting?: boolean
  max_registrations?: number
  outbound_cid_mode?: string
  class_of_service?: string
  recording_policy?: string
  notes?: string | null
  pickup_group?: string | null
  site_id?: string | null
}

export function useExtensions() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.extensions.list(tenantId),
    queryFn: () => apiClient.get<Extension[]>(`tenants/${tenantId}/extensions`),
    enabled: !!tenantId,
  })
}

export function useCreateExtension() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ExtensionCreate) =>
      apiClient.post<Extension>(`tenants/${tenantId}/extensions`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.extensions.all(tenantId) }),
  })
}

export function useUpdateExtension() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<ExtensionCreate>) =>
      apiClient.patch<Extension>(`tenants/${tenantId}/extensions/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.extensions.all(tenantId) }),
  })
}

export function useDeleteExtension() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/extensions/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.extensions.all(tenantId) }),
  })
}
