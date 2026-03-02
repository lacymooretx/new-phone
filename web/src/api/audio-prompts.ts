import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// Types matching backend AudioPromptResponse
export interface AudioPrompt {
  id: string
  tenant_id: string
  name: string
  description: string | null
  category: string
  storage_path: string | null
  storage_bucket: string | null
  file_size_bytes: number
  duration_seconds: number
  format: string
  sample_rate: number
  sha256_hash: string | null
  local_path: string | null
  site_id: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AudioPromptPlayback {
  url: string
  expires_in_seconds: number
}

export function useAudioPrompts() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.audioPrompts.list(tenantId),
    queryFn: () => apiClient.get<AudioPrompt[]>(`tenants/${tenantId}/audio-prompts`),
    enabled: !!tenantId,
  })
}

export function useUploadAudioPrompt() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (formData: FormData) => {
      const { accessToken } = useAuthStore.getState()
      const res = await fetch(`/api/v1/tenants/${tenantId}/audio-prompts`, {
        method: "POST",
        headers: {
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: formData,
      })
      if (!res.ok) {
        let detail = res.statusText
        try {
          const err = await res.json()
          detail = err.detail || err.title || detail
        } catch { /* ignore */ }
        throw new Error(detail)
      }
      return res.json() as Promise<AudioPrompt>
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.audioPrompts.all(tenantId) }),
  })
}

export function useDeleteAudioPrompt() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/audio-prompts/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.audioPrompts.all(tenantId) }),
  })
}

export function useAudioPromptPlayback(promptId: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.audioPrompts.playback(tenantId, promptId),
    queryFn: () => apiClient.get<AudioPromptPlayback>(`tenants/${tenantId}/audio-prompts/${promptId}/playback`),
    enabled: !!tenantId && !!promptId,
  })
}
