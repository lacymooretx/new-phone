import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// ── Types ──────────────────────────────────────────────────────────

export interface CWConfig {
  id: string
  tenant_id: string
  company_id: string
  client_id: string
  base_url: string
  api_version: string
  default_board_id: number | null
  default_status_id: number | null
  default_type_id: number | null
  auto_ticket_missed_calls: boolean
  auto_ticket_voicemails: boolean
  auto_ticket_completed_calls: boolean
  min_call_duration_seconds: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CWConfigCreate {
  company_id: string
  public_key: string
  private_key: string
  client_id: string
  base_url?: string
  api_version?: string
  default_board_id?: number | null
  default_status_id?: number | null
  default_type_id?: number | null
  auto_ticket_missed_calls?: boolean
  auto_ticket_voicemails?: boolean
  auto_ticket_completed_calls?: boolean
  min_call_duration_seconds?: number
}

export interface CWConfigUpdate {
  company_id?: string
  public_key?: string
  private_key?: string
  client_id?: string
  base_url?: string
  api_version?: string
  default_board_id?: number | null
  default_status_id?: number | null
  default_type_id?: number | null
  auto_ticket_missed_calls?: boolean
  auto_ticket_voicemails?: boolean
  auto_ticket_completed_calls?: boolean
  min_call_duration_seconds?: number
  is_active?: boolean
}

export interface CWCompanyMapping {
  id: string
  cw_config_id: string
  cw_company_id: number
  cw_company_name: string
  extension_id: string | null
  did_id: string | null
}

export interface CWCompanyMappingCreate {
  cw_company_id: number
  cw_company_name: string
  extension_id?: string | null
  did_id?: string | null
}

export interface CWBoard {
  id: number
  name: string
}

export interface CWBoardStatus {
  id: number
  name: string
}

export interface CWBoardType {
  id: number
  name: string
}

export interface CWCompanySearchResult {
  id: number
  name: string
  identifier: string
}

export interface CWTicketLog {
  id: string
  cw_config_id: string
  cdr_id: string | null
  cw_ticket_id: number
  cw_company_id: number | null
  trigger_type: string
  ticket_summary: string
  status: string
  error_message: string | null
  created_at: string
}

export interface CWTicketLogStats {
  today: number
  this_week: number
  this_month: number
  total: number
}

export interface CWTestResponse {
  success: boolean
  message: string
}

// ── Config CRUD ──────────────────────────────────────────────────

export function useCWConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.connectwise.config(tenantId),
    queryFn: () => apiClient.get<CWConfig>("/api/v1/connectwise/config"),
    enabled: !!tenantId,
    retry: false,
  })
}

export function useCreateCWConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CWConfigCreate) =>
      apiClient.post<CWConfig>("/api/v1/connectwise/config", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.connectwise.config(tenantId) }),
  })
}

export function useUpdateCWConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CWConfigUpdate) =>
      apiClient.patch<CWConfig>("/api/v1/connectwise/config", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.connectwise.config(tenantId) }),
  })
}

export function useDeleteCWConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiClient.delete("/api/v1/connectwise/config"),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.connectwise.config(tenantId) }),
  })
}

export function useTestCWConfig() {
  return useMutation({
    mutationFn: () =>
      apiClient.post<CWTestResponse>("/api/v1/connectwise/config/test"),
  })
}

// ── Company Mappings ──────────────────────────────────────────────

export function useCWCompanyMappings() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.connectwise.companyMappings(tenantId),
    queryFn: () => apiClient.get<CWCompanyMapping[]>("/api/v1/connectwise/company-mappings"),
    enabled: !!tenantId,
  })
}

export function useAddCWCompanyMapping() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CWCompanyMappingCreate) =>
      apiClient.post<CWCompanyMapping>("/api/v1/connectwise/company-mappings", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.connectwise.companyMappings(tenantId) }),
  })
}

export function useDeleteCWCompanyMapping() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (mappingId: string) =>
      apiClient.delete(`/api/v1/connectwise/company-mappings/${mappingId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.connectwise.companyMappings(tenantId) }),
  })
}

// ── Company Search ──────────────────────────────────────────────

export function useCWCompanySearch(query: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.connectwise.companySearch(tenantId, query),
    queryFn: () => apiClient.get<CWCompanySearchResult[]>("/api/v1/connectwise/companies/search", { q: query }),
    enabled: !!tenantId && query.length >= 2,
    staleTime: 30_000,
  })
}

// ── Boards / Statuses / Types ──────────────────────────────────

export function useCWBoards() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.connectwise.boards(tenantId),
    queryFn: () => apiClient.get<CWBoard[]>("/api/v1/connectwise/boards"),
    enabled: !!tenantId,
    staleTime: 300_000,
  })
}

export function useCWBoardStatuses(boardId: number | null) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.connectwise.boardStatuses(tenantId, boardId!),
    queryFn: () => apiClient.get<CWBoardStatus[]>(`/api/v1/connectwise/boards/${boardId}/statuses`),
    enabled: !!tenantId && !!boardId,
    staleTime: 300_000,
  })
}

export function useCWBoardTypes(boardId: number | null) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.connectwise.boardTypes(tenantId, boardId!),
    queryFn: () => apiClient.get<CWBoardType[]>(`/api/v1/connectwise/boards/${boardId}/types`),
    enabled: !!tenantId && !!boardId,
    staleTime: 300_000,
  })
}

// ── Ticket Logs ──────────────────────────────────────────────────

export function useCWTicketLogs(params?: Record<string, string>) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.connectwise.ticketLogs(tenantId, params),
    queryFn: () => apiClient.get<CWTicketLog[]>("/api/v1/connectwise/ticket-logs", params),
    enabled: !!tenantId,
  })
}

export function useCWTicketLogStats() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.connectwise.ticketLogStats(tenantId),
    queryFn: () => apiClient.get<CWTicketLogStats>("/api/v1/connectwise/ticket-logs/stats"),
    enabled: !!tenantId,
  })
}
