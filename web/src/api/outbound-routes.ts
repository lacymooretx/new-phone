import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// Types matching backend OutboundRouteResponse
export interface OutboundRouteTrunk {
  trunk_id: string
  position: number
}

export interface OutboundRoute {
  id: string
  tenant_id: string
  name: string
  dial_pattern: string
  prepend_digits: string | null
  strip_digits: number
  cid_mode: string
  custom_cid: string | null
  priority: number
  enabled: boolean
  trunk_ids: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface OutboundRouteCreate {
  name: string
  dial_pattern: string
  prepend_digits?: string | null
  strip_digits?: number
  cid_mode?: string
  custom_cid?: string | null
  priority?: number
  enabled?: boolean
  trunk_ids?: string[]
}

export function useOutboundRoutes() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.outboundRoutes.list(tenantId),
    queryFn: () => apiClient.get<OutboundRoute[]>(`tenants/${tenantId}/outbound-routes`),
    enabled: !!tenantId,
  })
}

export function useCreateOutboundRoute() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: OutboundRouteCreate) =>
      apiClient.post<OutboundRoute>(`tenants/${tenantId}/outbound-routes`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.outboundRoutes.all(tenantId) }),
  })
}

export function useUpdateOutboundRoute() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<OutboundRouteCreate>) =>
      apiClient.patch<OutboundRoute>(`tenants/${tenantId}/outbound-routes/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.outboundRoutes.all(tenantId) }),
  })
}

export function useDeleteOutboundRoute() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/outbound-routes/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.outboundRoutes.all(tenantId) }),
  })
}
