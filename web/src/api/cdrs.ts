import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

export interface CDR {
  id: string
  tenant_id: string
  call_id: string
  direction: string
  caller_number: string
  caller_name: string
  called_number: string
  extension_id: string | null
  did_id: string | null
  trunk_id: string | null
  ring_group_id: string | null
  queue_id: string | null
  disposition: string
  hangup_cause: string | null
  duration_seconds: number
  billable_seconds: number
  ring_seconds: number
  start_time: string
  answer_time: string | null
  end_time: string
  has_recording: boolean
  created_at: string
  agent_disposition_code_id: string | null
  agent_disposition_notes: string | null
  disposition_entered_at: string | null
  agent_disposition_label: string | null
  site_id: string | null
  compliance_score: number | null
  compliance_evaluation_id: string | null
}

export interface CDRFilters {
  date_from?: string
  date_to?: string
  direction?: string
  disposition?: string
  limit?: number
  offset?: number
}

export function useCdrs(filters: CDRFilters = {}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const params: Record<string, string> = {}
  if (filters.date_from) params.date_from = filters.date_from
  if (filters.date_to) params.date_to = filters.date_to
  if (filters.direction) params.direction = filters.direction
  if (filters.disposition) params.disposition = filters.disposition
  params.limit = String(filters.limit ?? 50)
  params.offset = String(filters.offset ?? 0)

  return useQuery({
    queryKey: queryKeys.cdrs.list(tenantId, params),
    queryFn: () => apiClient.get<CDR[]>(`tenants/${tenantId}/cdrs`, params),
    enabled: !!tenantId,
  })
}

export function useSetCDRDisposition() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      cdrId,
      disposition_code_id,
      notes,
    }: {
      cdrId: string
      disposition_code_id: string
      notes?: string | null
    }) =>
      apiClient.patch<CDR>(`tenants/${tenantId}/cdrs/${cdrId}/disposition`, {
        disposition_code_id,
        notes,
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.cdrs.all(tenantId) }),
  })
}

export async function exportCdrsAsCsv(tenantId: string, filters: CDRFilters = {}): Promise<void> {
  const params: Record<string, string> = {}
  if (filters.date_from) params.date_from = filters.date_from
  if (filters.date_to) params.date_to = filters.date_to
  if (filters.direction) params.direction = filters.direction
  if (filters.disposition) params.disposition = filters.disposition
  params.limit = "10000"
  params.offset = "0"

  const cdrs = await apiClient.get<CDR[]>(`tenants/${tenantId}/cdrs`, params)

  const headers = ["Start Time", "Direction", "Caller", "Called", "Disposition", "Duration (s)", "Billable (s)"]
  const rows = cdrs.map(c => [c.start_time, c.direction, c.caller_number, c.called_number, c.disposition, c.duration_seconds, c.billable_seconds].join(","))
  const csv = [headers.join(","), ...rows].join("\n")

  const blob = new Blob([csv], { type: "text/csv" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `cdrs-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
