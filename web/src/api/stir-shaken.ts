import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "./client"
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
  const tenantId = useAuthStore((s) => s.activeTenantId)
  return useQuery({
    queryKey: queryKeys.stirShaken.config(tenantId!),
    queryFn: () => api.get(`/tenants/${tenantId}/stir-shaken/config`).then((r) => r.data as StirShakenConfig),
    enabled: !!tenantId,
  })
}

export function useUpdateStirShakenConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<StirShakenConfig>) => api.put(`/tenants/${tenantId}/stir-shaken/config`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.stirShaken.config(tenantId!) }),
  })
}

export function useSpamFilter() {
  const tenantId = useAuthStore((s) => s.activeTenantId)
  return useQuery({
    queryKey: queryKeys.stirShaken.spamFilter(tenantId!),
    queryFn: () => api.get(`/tenants/${tenantId}/stir-shaken/spam-filter`).then((r) => r.data as SpamFilter),
    enabled: !!tenantId,
  })
}

export function useSpamBlockList() {
  const tenantId = useAuthStore((s) => s.activeTenantId)
  return useQuery({
    queryKey: queryKeys.stirShaken.blockList(tenantId!),
    queryFn: () => api.get(`/tenants/${tenantId}/stir-shaken/block-list`).then((r) => r.data as SpamBlockListEntry[]),
    enabled: !!tenantId,
  })
}

export function useAddBlockListEntry() {
  const tenantId = useAuthStore((s) => s.activeTenantId)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { pattern: string; reason?: string }) => api.post(`/tenants/${tenantId}/stir-shaken/block-list`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.stirShaken.blockList(tenantId!) }),
  })
}

export function useSpamAllowList() {
  const tenantId = useAuthStore((s) => s.activeTenantId)
  return useQuery({
    queryKey: queryKeys.stirShaken.allowList(tenantId!),
    queryFn: () => api.get(`/tenants/${tenantId}/stir-shaken/allow-list`).then((r) => r.data as SpamAllowListEntry[]),
    enabled: !!tenantId,
  })
}

export function useAddAllowListEntry() {
  const tenantId = useAuthStore((s) => s.activeTenantId)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { pattern: string; reason?: string }) => api.post(`/tenants/${tenantId}/stir-shaken/allow-list`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.stirShaken.allowList(tenantId!) }),
  })
}
