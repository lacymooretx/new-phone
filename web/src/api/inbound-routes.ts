import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// Types matching backend InboundRouteResponse
export interface InboundRoute {
  id: string
  tenant_id: string
  name: string
  did_id: string | null
  destination_type: string
  destination_id: string | null
  cid_name_prefix: string | null
  time_conditions: Record<string, unknown> | null
  enabled: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface InboundRouteCreate {
  name: string
  destination_type: string
  did_id?: string | null
  destination_id?: string | null
  cid_name_prefix?: string | null
  time_conditions?: Record<string, unknown> | null
  enabled?: boolean
}

export function useInboundRoutes() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.inboundRoutes.list(tenantId),
    queryFn: () => apiClient.get<InboundRoute[]>(`tenants/${tenantId}/inbound-routes`),
    enabled: !!tenantId,
  })
}

export function useCreateInboundRoute() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: InboundRouteCreate) =>
      apiClient.post<InboundRoute>(`tenants/${tenantId}/inbound-routes`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.inboundRoutes.all(tenantId) }),
  })
}

export function useUpdateInboundRoute() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<InboundRouteCreate>) =>
      apiClient.patch<InboundRoute>(`tenants/${tenantId}/inbound-routes/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.inboundRoutes.all(tenantId) }),
  })
}

export function useDeleteInboundRoute() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/inbound-routes/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.inboundRoutes.all(tenantId) }),
  })
}
