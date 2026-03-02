import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "./query-keys"

// Types matching backend AuditLogResponse
export interface AuditLog {
  id: string
  user_id: string | null
  tenant_id: string | null
  action: string
  resource_type: string
  resource_id: string | null
  changes: Record<string, unknown> | null
  ip_address: string | null
  user_agent: string | null
  created_at: string
}

export interface AuditLogFilters {
  action?: string
  resource_type?: string
  date_from?: string
  date_to?: string
  page?: number
  per_page?: number
}

export function useAuditLogs(filters?: AuditLogFilters) {
  const params: Record<string, string> = {}
  if (filters?.action) params.action = filters.action
  if (filters?.resource_type) params.resource_type = filters.resource_type
  if (filters?.date_from) params.date_from = filters.date_from
  if (filters?.date_to) params.date_to = filters.date_to
  if (filters?.page) params.page = String(filters.page)
  if (filters?.per_page) params.per_page = String(filters.per_page)

  return useQuery({
    queryKey: queryKeys.auditLogs.list(params),
    queryFn: () => apiClient.get<AuditLog[]>("audit-logs", params),
  })
}
