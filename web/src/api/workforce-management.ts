import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WfmShift {
  id: string
  tenant_id: string
  name: string
  start_time: string
  end_time: string
  break_minutes: number
  color: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface WfmShiftCreate {
  name: string
  start_time: string
  end_time: string
  break_minutes?: number
  color?: string | null
}

export interface WfmScheduleEntry {
  id: string
  tenant_id: string
  extension_id: string
  shift_id: string
  date: string
  notes: string | null
  created_at: string
  updated_at: string
  shift: WfmShift | null
  extension_number: string
  extension_name: string
}

export interface WfmScheduleEntryCreate {
  extension_id: string
  shift_id: string
  date: string
  notes?: string | null
}

export interface WfmTimeOffRequest {
  id: string
  tenant_id: string
  extension_id: string
  start_date: string
  end_date: string
  reason: string | null
  status: string
  reviewed_by_id: string | null
  reviewed_at: string | null
  review_notes: string | null
  created_at: string
  updated_at: string
  extension_number: string
  extension_name: string
}

export interface WfmTimeOffRequestCreate {
  extension_id: string
  start_date: string
  end_date: string
  reason?: string | null
}

export interface WfmTimeOffReview {
  status: "approved" | "denied"
  review_notes?: string | null
}

export interface WfmForecastConfig {
  id: string
  tenant_id: string
  queue_id: string
  target_sla_percent: number
  target_sla_seconds: number
  shrinkage_percent: number
  lookback_weeks: number
  created_at: string
  updated_at: string
  queue_name: string
}

export interface WfmForecastConfigCreate {
  queue_id: string
  target_sla_percent?: number
  target_sla_seconds?: number
  shrinkage_percent?: number
  lookback_weeks?: number
}

export interface WfmHourlyVolume {
  hour: number
  avg_calls: number
  avg_aht_seconds: number
  avg_abandon_rate: number
}

export interface WfmDailyVolume {
  day_of_week: string
  avg_calls: number
  avg_aht_seconds: number
}

export interface WfmForecastPoint {
  hour: number
  predicted_calls: number
  recommended_agents: number
  target_sla_percent: number
  target_sla_seconds: number
}

export interface WfmStaffingSummary {
  queue_id: string
  queue_name: string
  current_agents: number
  recommended_agents: number
  forecast_volume: number
}

export interface WfmScheduleOverview {
  date: string
  total_scheduled: number
  time_off_approved: number
  net_available: number
}

// ---------------------------------------------------------------------------
// Shift hooks
// ---------------------------------------------------------------------------

export function useWfmShifts(isActive?: boolean) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const params = new URLSearchParams()
  if (isActive !== undefined) params.set("is_active", String(isActive))
  const qs = params.toString()
  return useQuery({
    queryKey: queryKeys.wfm.shifts(tenantId),
    queryFn: () =>
      apiClient.get<WfmShift[]>(
        `tenants/${tenantId}/wfm/shifts${qs ? `?${qs}` : ""}`
      ),
    enabled: !!tenantId,
  })
}

export function useCreateWfmShift() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: WfmShiftCreate) =>
      apiClient.post<WfmShift>(`tenants/${tenantId}/wfm/shifts`, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.wfm.all(tenantId) }),
  })
}

export function useUpdateWfmShift() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<WfmShiftCreate>) =>
      apiClient.patch<WfmShift>(`tenants/${tenantId}/wfm/shifts/${id}`, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.wfm.all(tenantId) }),
  })
}

export function useDeleteWfmShift() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/wfm/shifts/${id}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.wfm.all(tenantId) }),
  })
}

// ---------------------------------------------------------------------------
// Schedule hooks
// ---------------------------------------------------------------------------

export function useWfmSchedule(
  dateFrom: string,
  dateTo: string,
  extensionId?: string
) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const params = new URLSearchParams({ date_from: dateFrom, date_to: dateTo })
  if (extensionId) params.set("extension_id", extensionId)
  return useQuery({
    queryKey: queryKeys.wfm.schedule(tenantId, dateFrom, dateTo, extensionId),
    queryFn: () =>
      apiClient.get<WfmScheduleEntry[]>(
        `tenants/${tenantId}/wfm/schedule?${params.toString()}`
      ),
    enabled: !!tenantId && !!dateFrom && !!dateTo,
  })
}

export function useCreateWfmScheduleEntry() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: WfmScheduleEntryCreate) =>
      apiClient.post<WfmScheduleEntry>(
        `tenants/${tenantId}/wfm/schedule`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.wfm.all(tenantId) }),
  })
}

export function useBulkCreateWfmScheduleEntries() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: WfmScheduleEntryCreate[]) =>
      apiClient.post<WfmScheduleEntry[]>(
        `tenants/${tenantId}/wfm/schedule/bulk`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.wfm.all(tenantId) }),
  })
}

export function useUpdateWfmScheduleEntry() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      ...data
    }: { id: string } & Partial<WfmScheduleEntryCreate>) =>
      apiClient.patch<WfmScheduleEntry>(
        `tenants/${tenantId}/wfm/schedule/${id}`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.wfm.all(tenantId) }),
  })
}

export function useDeleteWfmScheduleEntry() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/wfm/schedule/${id}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.wfm.all(tenantId) }),
  })
}

export function useWfmScheduleOverview(dateFrom: string, dateTo: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const params = new URLSearchParams({ date_from: dateFrom, date_to: dateTo })
  return useQuery({
    queryKey: queryKeys.wfm.scheduleOverview(tenantId, dateFrom, dateTo),
    queryFn: () =>
      apiClient.get<WfmScheduleOverview[]>(
        `tenants/${tenantId}/wfm/schedule/overview?${params.toString()}`
      ),
    enabled: !!tenantId && !!dateFrom && !!dateTo,
  })
}

// ---------------------------------------------------------------------------
// Time-off hooks
// ---------------------------------------------------------------------------

export function useWfmTimeOffRequests(params?: {
  extension_id?: string
  status?: string
  date_from?: string
  date_to?: string
}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const sp = new URLSearchParams()
  if (params?.extension_id) sp.set("extension_id", params.extension_id)
  if (params?.status) sp.set("status", params.status)
  if (params?.date_from) sp.set("date_from", params.date_from)
  if (params?.date_to) sp.set("date_to", params.date_to)
  const qs = sp.toString()
  const filters: Record<string, string> = {}
  if (params?.extension_id) filters.extension_id = params.extension_id
  if (params?.status) filters.status = params.status
  if (params?.date_from) filters.date_from = params.date_from
  if (params?.date_to) filters.date_to = params.date_to
  return useQuery({
    queryKey: queryKeys.wfm.timeOff(tenantId, Object.keys(filters).length ? filters : undefined),
    queryFn: () =>
      apiClient.get<WfmTimeOffRequest[]>(
        `tenants/${tenantId}/wfm/time-off${qs ? `?${qs}` : ""}`
      ),
    enabled: !!tenantId,
  })
}

export function useCreateWfmTimeOffRequest() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: WfmTimeOffRequestCreate) =>
      apiClient.post<WfmTimeOffRequest>(
        `tenants/${tenantId}/wfm/time-off`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.wfm.all(tenantId) }),
  })
}

export function useReviewWfmTimeOffRequest() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & WfmTimeOffReview) =>
      apiClient.patch<WfmTimeOffRequest>(
        `tenants/${tenantId}/wfm/time-off/${id}/review`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.wfm.all(tenantId) }),
  })
}

// ---------------------------------------------------------------------------
// Forecast config hooks
// ---------------------------------------------------------------------------

export function useWfmForecastConfigs() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.wfm.forecastConfigs(tenantId),
    queryFn: () =>
      apiClient.get<WfmForecastConfig[]>(
        `tenants/${tenantId}/wfm/forecast/configs`
      ),
    enabled: !!tenantId,
  })
}

export function useUpsertWfmForecastConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      queue_id,
      ...data
    }: WfmForecastConfigCreate) =>
      apiClient.put<WfmForecastConfig>(
        `tenants/${tenantId}/wfm/forecast/configs/${queue_id}`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.wfm.all(tenantId) }),
  })
}

// ---------------------------------------------------------------------------
// Analytics / forecast hooks
// ---------------------------------------------------------------------------

export function useWfmHourlyVolume(
  queueId: string,
  dateFrom: string,
  dateTo: string
) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const params = new URLSearchParams({ date_from: dateFrom, date_to: dateTo })
  return useQuery({
    queryKey: queryKeys.wfm.hourlyVolume(tenantId, queueId, dateFrom, dateTo),
    queryFn: () =>
      apiClient.get<WfmHourlyVolume[]>(
        `tenants/${tenantId}/wfm/analytics/hourly-volume/${queueId}?${params.toString()}`
      ),
    enabled: !!tenantId && !!queueId && !!dateFrom && !!dateTo,
  })
}

export function useWfmDailyVolume(
  queueId: string,
  dateFrom: string,
  dateTo: string
) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const params = new URLSearchParams({ date_from: dateFrom, date_to: dateTo })
  return useQuery({
    queryKey: queryKeys.wfm.dailyVolume(tenantId, queueId, dateFrom, dateTo),
    queryFn: () =>
      apiClient.get<WfmDailyVolume[]>(
        `tenants/${tenantId}/wfm/analytics/daily-volume/${queueId}?${params.toString()}`
      ),
    enabled: !!tenantId && !!queueId && !!dateFrom && !!dateTo,
  })
}

export function useWfmForecast(queueId: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.wfm.forecast(tenantId, queueId),
    queryFn: () =>
      apiClient.get<WfmForecastPoint[]>(
        `tenants/${tenantId}/wfm/forecast/${queueId}`
      ),
    enabled: !!tenantId && !!queueId,
  })
}

export function useWfmStaffingSummary() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.wfm.staffingSummary(tenantId),
    queryFn: () =>
      apiClient.get<WfmStaffingSummary[]>(
        `tenants/${tenantId}/wfm/forecast/summary`
      ),
    enabled: !!tenantId,
  })
}
