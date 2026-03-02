import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

export interface Recording {
  id: string
  tenant_id: string
  cdr_id: string | null
  call_id: string
  storage_path: string | null
  storage_bucket: string | null
  file_size_bytes: number
  duration_seconds: number
  format: string
  sample_rate: number
  sha256_hash: string | null
  recording_policy: string
  is_active: boolean
  created_at: string
}

export interface PlaybackResponse {
  url: string
  expires_in_seconds: number
}

export interface RecordingFilters {
  date_from?: string
  date_to?: string
}

export function useRecordings(filters?: RecordingFilters) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const params = new URLSearchParams()
  if (filters?.date_from) params.set("date_from", filters.date_from)
  if (filters?.date_to) params.set("date_to", filters.date_to)
  const qs = params.toString()
  return useQuery({
    queryKey: [...queryKeys.recordings.list(tenantId), filters],
    queryFn: () => apiClient.get<Recording[]>(`tenants/${tenantId}/recordings${qs ? `?${qs}` : ""}`),
    enabled: !!tenantId,
  })
}

export function useRecordingPlayback(recordingId: string | null) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.recordings.playback(tenantId, recordingId!),
    queryFn: () => apiClient.get<PlaybackResponse>(`tenants/${tenantId}/recordings/${recordingId}/playback`),
    enabled: !!tenantId && !!recordingId,
  })
}

export function useDeleteRecording() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/recordings/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.recordings.all(tenantId) }),
  })
}
