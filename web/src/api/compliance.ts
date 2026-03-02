import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// ── Types ──

export interface DNCList {
  id: string
  tenant_id: string
  name: string
  description: string | null
  list_type: string
  source_url: string | null
  last_refreshed_at: string | null
  is_active: boolean
  entry_count: number
  created_at: string
  updated_at: string
}

export interface DNCListCreate {
  name: string
  description?: string | null
  list_type?: string
  source_url?: string | null
}

export interface DNCListUpdate {
  name?: string
  description?: string | null
  list_type?: string
  source_url?: string | null
  is_active?: boolean
}

export interface DNCEntry {
  id: string
  tenant_id: string
  dnc_list_id: string
  phone_number: string
  added_by_user_id: string | null
  reason: string | null
  source: string
  expires_at: string | null
  created_at: string
  updated_at: string
}

export interface DNCEntryCreate {
  phone_number: string
  reason?: string | null
  source?: string
  expires_at?: string | null
}

export interface DNCEntryBulkCreate {
  phone_numbers: string[]
  reason?: string | null
  source?: string
}

export interface BulkUploadResult {
  added: number
  skipped: number
  total: number
}

export interface DNCCheckResult {
  is_blocked: boolean
  matched_lists: string[]
  has_consent: boolean
  calling_window_ok: boolean
  details: Record<string, unknown> | null
}

export interface ConsentRecord {
  id: string
  tenant_id: string
  phone_number: string
  campaign_type: string
  consent_method: string
  consent_text: string | null
  consented_at: string
  revoked_at: string | null
  is_active: boolean
  metadata_json: Record<string, unknown> | null
  recorded_by_user_id: string | null
  created_at: string
  updated_at: string
}

export interface ConsentRecordCreate {
  phone_number: string
  campaign_type: string
  consent_method: string
  consent_text?: string | null
  consented_at?: string | null
  metadata?: Record<string, unknown> | null
}

export interface ComplianceSettings {
  id: string
  tenant_id: string
  calling_window_start: string
  calling_window_end: string
  default_timezone: string
  enforce_calling_window: boolean
  sync_sms_optout_to_dnc: boolean
  auto_dnc_on_request: boolean
  national_dnc_enabled: boolean
  created_at: string
  updated_at: string
}

export interface ComplianceSettingsUpdate {
  calling_window_start?: string
  calling_window_end?: string
  default_timezone?: string
  enforce_calling_window?: boolean
  sync_sms_optout_to_dnc?: boolean
  auto_dnc_on_request?: boolean
  national_dnc_enabled?: boolean
}

export interface ComplianceAuditLogEntry {
  id: string
  tenant_id: string
  event_type: string
  phone_number: string | null
  user_id: string | null
  details: Record<string, unknown> | null
  created_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
}

// ── DNC List hooks ──

export function useDNCLists() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.compliance.lists(tenantId),
    queryFn: () =>
      apiClient.get<DNCList[]>(`tenants/${tenantId}/compliance/dnc-lists`),
    enabled: !!tenantId,
  })
}

export function useDNCList(listId: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.compliance.listDetail(tenantId, listId),
    queryFn: () =>
      apiClient.get<DNCList>(`tenants/${tenantId}/compliance/dnc-lists/${listId}`),
    enabled: !!tenantId && !!listId,
  })
}

export function useCreateDNCList() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: DNCListCreate) =>
      apiClient.post<DNCList>(`tenants/${tenantId}/compliance/dnc-lists`, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.compliance.all(tenantId) }),
  })
}

export function useUpdateDNCList() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & DNCListUpdate) =>
      apiClient.patch<DNCList>(`tenants/${tenantId}/compliance/dnc-lists/${id}`, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.compliance.all(tenantId) }),
  })
}

export function useDeleteDNCList() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/compliance/dnc-lists/${id}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.compliance.all(tenantId) }),
  })
}

// ── DNC Entry hooks ──

export function useDNCEntries(listId: string, page: number = 1, perPage: number = 50) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.compliance.entries(tenantId, listId, page),
    queryFn: () =>
      apiClient.get<PaginatedResponse<DNCEntry>>(
        `tenants/${tenantId}/compliance/dnc-lists/${listId}/entries`,
        { page: String(page), per_page: String(perPage) }
      ),
    enabled: !!tenantId && !!listId,
  })
}

export function useAddDNCEntry() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ listId, ...data }: DNCEntryCreate & { listId: string }) =>
      apiClient.post<DNCEntry>(
        `tenants/${tenantId}/compliance/dnc-lists/${listId}/entries`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.compliance.all(tenantId) }),
  })
}

export function useBulkAddDNCEntries() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ listId, ...data }: DNCEntryBulkCreate & { listId: string }) =>
      apiClient.post<BulkUploadResult>(
        `tenants/${tenantId}/compliance/dnc-lists/${listId}/entries/bulk`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.compliance.all(tenantId) }),
  })
}

export function useRemoveDNCEntry() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ listId, entryId }: { listId: string; entryId: string }) =>
      apiClient.delete(`tenants/${tenantId}/compliance/dnc-lists/${listId}/entries/${entryId}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.compliance.all(tenantId) }),
  })
}

// ── DNC Check hook ──

export function useCheckNumber() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useMutation({
    mutationFn: (phone_number: string) =>
      apiClient.post<DNCCheckResult>(`tenants/${tenantId}/compliance/dnc-check`, { phone_number }),
  })
}

// ── Consent Record hooks ──

export function useConsentRecords(params?: {
  phone_number?: string
  campaign_type?: string
  is_active?: string
  page?: number
  per_page?: number
}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const queryParams: Record<string, string> = {}
  if (params?.phone_number) queryParams.phone_number = params.phone_number
  if (params?.campaign_type) queryParams.campaign_type = params.campaign_type
  if (params?.is_active !== undefined) queryParams.is_active = params.is_active
  if (params?.page) queryParams.page = String(params.page)
  if (params?.per_page) queryParams.per_page = String(params.per_page)

  return useQuery({
    queryKey: queryKeys.compliance.consentRecords(tenantId, queryParams),
    queryFn: () =>
      apiClient.get<PaginatedResponse<ConsentRecord>>(
        `tenants/${tenantId}/compliance/consent-records`,
        queryParams
      ),
    enabled: !!tenantId,
  })
}

export function useCreateConsentRecord() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ConsentRecordCreate) =>
      apiClient.post<ConsentRecord>(`tenants/${tenantId}/compliance/consent-records`, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.compliance.all(tenantId) }),
  })
}

export function useRevokeConsent() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (recordId: string) =>
      apiClient.post<ConsentRecord>(
        `tenants/${tenantId}/compliance/consent-records/${recordId}/revoke`
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.compliance.all(tenantId) }),
  })
}

// ── Compliance Settings hooks ──

export function useComplianceSettings() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.compliance.settings(tenantId),
    queryFn: () =>
      apiClient.get<ComplianceSettings>(`tenants/${tenantId}/compliance/settings`),
    enabled: !!tenantId,
  })
}

export function useUpdateComplianceSettings() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ComplianceSettingsUpdate) =>
      apiClient.put<ComplianceSettings>(`tenants/${tenantId}/compliance/settings`, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.compliance.all(tenantId) }),
  })
}

// ── Audit Log hook ──

export function useComplianceAuditLog(params?: {
  event_type?: string
  phone_number?: string
  start_date?: string
  end_date?: string
  page?: number
  per_page?: number
}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const queryParams: Record<string, string> = {}
  if (params?.event_type) queryParams.event_type = params.event_type
  if (params?.phone_number) queryParams.phone_number = params.phone_number
  if (params?.start_date) queryParams.start_date = params.start_date
  if (params?.end_date) queryParams.end_date = params.end_date
  if (params?.page) queryParams.page = String(params.page)
  if (params?.per_page) queryParams.per_page = String(params.per_page)

  return useQuery({
    queryKey: queryKeys.compliance.auditLog(tenantId, queryParams),
    queryFn: () =>
      apiClient.get<PaginatedResponse<ComplianceAuditLogEntry>>(
        `tenants/${tenantId}/compliance/audit-log`,
        queryParams
      ),
    enabled: !!tenantId,
  })
}

// ── SMS Opt-Out Sync hook ──

export function useSyncSmsOptouts() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiClient.post<BulkUploadResult>(`tenants/${tenantId}/compliance/sync-sms-optouts`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.compliance.all(tenantId) }),
  })
}
