import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// Types matching backend DIDResponse
export interface DID {
  id: string
  tenant_id: string
  number: string
  provider: string
  provider_sid: string | null
  status: string
  is_emergency: boolean
  sms_enabled: boolean
  sms_queue_id: string | null
  site_id: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface DIDCreate {
  number: string // E.164 format
  provider: string
  provider_sid?: string | null
  status?: string
  is_emergency?: boolean
  sms_enabled?: boolean
  sms_queue_id?: string | null
  site_id?: string | null
}

export function useDids() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.dids.list(tenantId),
    queryFn: () => apiClient.get<DID[]>(`tenants/${tenantId}/dids`),
    enabled: !!tenantId,
  })
}

export function useCreateDid() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: DIDCreate) =>
      apiClient.post<DID>(`tenants/${tenantId}/dids`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.dids.all(tenantId) }),
  })
}

export function useUpdateDid() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<DIDCreate>) =>
      apiClient.patch<DID>(`tenants/${tenantId}/dids/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.dids.all(tenantId) }),
  })
}

export function useDeleteDid() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/dids/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.dids.all(tenantId) }),
  })
}

// --- Provider operations ---

export interface DIDSearchParams {
  area_code?: string
  state?: string
  quantity?: number
  provider?: string
}

export interface DIDSearchResult {
  number: string
  monthly_cost: number
  setup_cost: number
  provider: string
  capabilities: string[]
  region: string
}

export interface DIDPurchaseRequest {
  number: string
  provider: string
}

export function useSearchDids(params: DIDSearchParams, enabled = false) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.dids.search(tenantId, params as Record<string, unknown>),
    queryFn: () =>
      apiClient.get<DIDSearchResult[]>(
        `tenants/${tenantId}/dids/search`,
        Object.fromEntries(
          Object.entries(params)
            .filter(([, v]) => v != null && v !== "")
            .map(([k, v]) => [k, String(v)])
        )
      ),
    enabled: enabled && !!tenantId,
  })
}

export function usePurchaseDid() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: DIDPurchaseRequest) =>
      apiClient.post<DID>(`tenants/${tenantId}/dids/purchase`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.dids.all(tenantId) }),
  })
}

export function useReleaseDid() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.post<void>(`tenants/${tenantId}/dids/${id}/release`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.dids.all(tenantId) }),
  })
}
