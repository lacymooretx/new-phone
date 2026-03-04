import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { isMspRole } from "@/lib/constants"
import { useExtensions, type Extension } from "./extensions"
import { queryKeys } from "./query-keys"

/**
 * For MSP roles: fetch extensions for a specific tenant (cross-tenant view).
 * For non-MSP roles: falls back to useExtensions() (current tenant).
 */
export function useTenantExtensions(tenantId?: string | null) {
  const role = useAuthStore((s) => s.user?.role)
  const activeTenantId = useAuthStore((s) => s.activeTenantId)
  const isMsp = role ? isMspRole(role) : false

  const targetTenantId = isMsp && tenantId ? tenantId : activeTenantId

  // For MSP users viewing a different tenant
  const crossTenantQuery = useQuery({
    queryKey: queryKeys.extensions.list(targetTenantId!),
    queryFn: () => apiClient.get<Extension[]>(`tenants/${targetTenantId}/extensions`),
    enabled: !!targetTenantId && isMsp && tenantId !== activeTenantId && !!tenantId,
  })

  // For same-tenant or non-MSP users
  const sameTenantQuery = useExtensions()

  if (isMsp && tenantId && tenantId !== activeTenantId) {
    return crossTenantQuery
  }
  return sameTenantQuery
}
