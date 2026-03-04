import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

export interface ApiKeyResponse {
  id: string
  tenant_id: string
  name: string
  key_prefix: string
  scopes: string[]
  rate_limit: number
  is_active: boolean
  description: string | null
  expires_at: string | null
  last_used_at: string | null
  created_at: string
  updated_at: string
}

export interface ApiKeyCreatedResponse extends ApiKeyResponse {
  raw_key: string
}

export interface ApiKeyCreate {
  name: string
  scopes?: string[]
  rate_limit?: number
  description?: string | null
  expires_at?: string | null
}

export interface ApiKeyUpdate {
  name?: string
  scopes?: string[]
  rate_limit?: number
  description?: string | null
  is_active?: boolean
}

export function useApiKeys() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.apiKeys.list(tenantId),
    queryFn: () => apiClient.get<ApiKeyResponse[]>(`tenants/${tenantId}/api-keys`),
    enabled: !!tenantId,
  })
}

export function useCreateApiKey() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ApiKeyCreate) =>
      apiClient.post<ApiKeyCreatedResponse>(`tenants/${tenantId}/api-keys`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.apiKeys.list(tenantId) }),
  })
}

export function useUpdateApiKey() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ApiKeyUpdate }) =>
      apiClient.put<ApiKeyResponse>(`tenants/${tenantId}/api-keys/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.apiKeys.list(tenantId) }),
  })
}

export function useDeleteApiKey() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiClient.delete(`tenants/${tenantId}/api-keys/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.apiKeys.list(tenantId) }),
  })
}
