import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

export interface Site {
  id: string
  tenant_id: string
  name: string
  description: string | null
  timezone: string
  address_street: string | null
  address_city: string | null
  address_state: string | null
  address_zip: string | null
  address_country: string
  outbound_cid_name: string | null
  outbound_cid_number: string | null
  moh_prompt_id: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface SiteSummary {
  id: string
  name: string
  timezone: string
}

export interface SiteCreate {
  name: string
  description?: string | null
  timezone?: string
  address_street?: string | null
  address_city?: string | null
  address_state?: string | null
  address_zip?: string | null
  address_country?: string
  outbound_cid_name?: string | null
  outbound_cid_number?: string | null
  moh_prompt_id?: string | null
}

export function useSites() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.sites.list(tenantId),
    queryFn: () => apiClient.get<Site[]>(`tenants/${tenantId}/sites`),
    enabled: !!tenantId,
  })
}

export function useSiteSummaries() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.sites.summaries(tenantId),
    queryFn: () => apiClient.get<SiteSummary[]>(`tenants/${tenantId}/sites/summaries`),
    enabled: !!tenantId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useCreateSite() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: SiteCreate) =>
      apiClient.post<Site>(`tenants/${tenantId}/sites`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.sites.all(tenantId) }),
  })
}

export function useUpdateSite() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<SiteCreate>) =>
      apiClient.patch<Site>(`tenants/${tenantId}/sites/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.sites.all(tenantId) }),
  })
}

export function useDeleteSite() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/sites/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.sites.all(tenantId) }),
  })
}
