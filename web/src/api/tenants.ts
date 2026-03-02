import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "./query-keys"

export interface Tenant {
  id: string
  name: string
  slug: string
  domain: string | null
  sip_domain: string | null
  default_moh_prompt_id: string | null
  is_active: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export interface TenantUpdate {
  name?: string
  slug?: string
  domain?: string | null
  sip_domain?: string | null
  notes?: string | null
  is_active?: boolean
}

export interface HealthResponse {
  status: string
  database: string
  redis: string
  freeswitch: string
  minio: string
}

export function useTenants() {
  return useQuery({
    queryKey: queryKeys.tenants.list(),
    queryFn: () => apiClient.get<Tenant[]>("tenants"),
  })
}

export function useTenant(id: string | null) {
  return useQuery({
    queryKey: queryKeys.tenants.detail(id!),
    queryFn: () => apiClient.get<Tenant>(`tenants/${id}`),
    enabled: !!id,
  })
}

export function useUpdateTenant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & TenantUpdate) =>
      apiClient.patch<Tenant>(`tenants/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.tenants.all }),
  })
}

export interface TenantCreate {
  name: string
  slug: string
  domain?: string | null
  sip_domain?: string | null
  notes?: string | null
}

export function useCreateTenant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TenantCreate) =>
      apiClient.post<Tenant>("tenants", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.tenants.all }),
  })
}

export function useDeactivateTenant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.tenants.all }),
  })
}

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.tenants.health(),
    queryFn: () => apiClient.get<HealthResponse>("health"),
    refetchInterval: 30000,
  })
}
