import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

export interface StirShakenConfig {
  id: string
  tenant_id: string
  enabled: boolean
  attestation_level: string
  certificate_pem: string | null
  created_at: string
  updated_at: string
}

export interface SpamFilter {
  id: string
  tenant_id: string
  min_attestation: string | null
  spam_score_threshold: number
  block_anonymous: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface SpamBlockListEntry {
  id: string
  tenant_id: string
  pattern: string
  reason: string | null
  created_at: string
}

export interface SpamAllowListEntry {
  id: string
  tenant_id: string
  pattern: string
  reason: string | null
  created_at: string
}

export function useStirShakenConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.stirShaken.config(tenantId),
    queryFn: () => apiClient.get<StirShakenConfig>(`tenants/${tenantId}/stir-shaken/config`),
    enabled: !!tenantId,
  })
}

export function useUpdateStirShakenConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<StirShakenConfig>) => apiClient.put<StirShakenConfig>(`tenants/${tenantId}/stir-shaken/config`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.stirShaken.config(tenantId) }),
  })
}

export function useSpamFilter() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.stirShaken.spamFilter(tenantId),
    queryFn: () => apiClient.get<SpamFilter>(`tenants/${tenantId}/stir-shaken/spam-filter`),
    enabled: !!tenantId,
  })
}

export function useSpamBlockList() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.stirShaken.blockList(tenantId),
    queryFn: () => apiClient.get<SpamBlockListEntry[]>(`tenants/${tenantId}/stir-shaken/block-list`),
    enabled: !!tenantId,
  })
}

export function useAddBlockListEntry() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { pattern: string; reason?: string }) => apiClient.post<SpamBlockListEntry>(`tenants/${tenantId}/stir-shaken/block-list`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.stirShaken.blockList(tenantId) }),
  })
}

export function useSpamAllowList() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.stirShaken.allowList(tenantId),
    queryFn: () => apiClient.get<SpamAllowListEntry[]>(`tenants/${tenantId}/stir-shaken/allow-list`),
    enabled: !!tenantId,
  })
}

export function useAddAllowListEntry() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { pattern: string; reason?: string }) => apiClient.post<SpamAllowListEntry>(`tenants/${tenantId}/stir-shaken/allow-list`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.stirShaken.allowList(tenantId) }),
  })
}
