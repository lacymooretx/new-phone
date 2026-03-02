import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// --- Types ---

export interface CallSummary {
  total_calls: number
  inbound: number
  outbound: number
  internal: number
  answered: number
  no_answer: number
  busy: number
  failed: number
  voicemail: number
  cancelled: number
  avg_duration_seconds: number
  total_duration_seconds: number
}

export interface CallVolumeTrendPoint {
  period: string
  total: number
  inbound: number
  outbound: number
  internal: number
}

export interface CallVolumeTrendResponse {
  granularity: string
  data: CallVolumeTrendPoint[]
}

export interface ExtensionActivity {
  extension_id: string
  extension_number: string
  extension_name: string | null
  total_calls: number
  inbound: number
  outbound: number
  missed: number
  avg_duration_seconds: number
  total_duration_seconds: number
}

export interface DIDUsage {
  did_id: string
  number: string
  total_calls: number
  answered: number
  missed: number
  avg_duration_seconds: number
}

export interface DurationBucket {
  bucket: string
  count: number
  percentage: number
}

export interface TopCaller {
  caller_number: string
  caller_name: string | null
  total_calls: number
  total_duration_seconds: number
  avg_duration_seconds: number
}

export interface HourlyDistributionPoint {
  hour: number
  total: number
  inbound: number
  outbound: number
}

export interface TenantOverview {
  tenant_id: string
  tenant_name: string
  total_calls: number
  calls_today: number
  extension_count: number
}

export interface MSPOverviewResponse {
  total_tenants: number
  total_calls_today: number
  total_calls_week: number
  total_extensions: number
  system_health: string
  tenants: TenantOverview[]
}

// --- Filters ---

export interface AnalyticsFilters {
  date_from?: string
  date_to?: string
  granularity?: string
  limit?: number
}

function buildParams(filters: AnalyticsFilters): Record<string, string> {
  const params: Record<string, string> = {}
  if (filters.date_from) params.date_from = filters.date_from
  if (filters.date_to) params.date_to = filters.date_to
  if (filters.granularity) params.granularity = filters.granularity
  if (filters.limit) params.limit = String(filters.limit)
  return params
}

// --- Hooks ---

export function useCallSummary(filters: AnalyticsFilters = {}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const params = buildParams(filters)
  return useQuery({
    queryKey: queryKeys.analytics.summary(tenantId, params),
    queryFn: () => apiClient.get<CallSummary>(`tenants/${tenantId}/analytics/summary`, params),
    enabled: !!tenantId,
  })
}

export function useCallVolumeTrend(filters: AnalyticsFilters = {}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const params = buildParams(filters)
  return useQuery({
    queryKey: queryKeys.analytics.volumeTrend(tenantId, params),
    queryFn: () => apiClient.get<CallVolumeTrendResponse>(`tenants/${tenantId}/analytics/volume-trend`, params),
    enabled: !!tenantId,
  })
}

export function useExtensionActivity(filters: AnalyticsFilters = {}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const params = buildParams(filters)
  return useQuery({
    queryKey: queryKeys.analytics.extensionActivity(tenantId, params),
    queryFn: () => apiClient.get<ExtensionActivity[]>(`tenants/${tenantId}/analytics/extension-activity`, params),
    enabled: !!tenantId,
  })
}

export function useDIDUsage(filters: AnalyticsFilters = {}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const params = buildParams(filters)
  return useQuery({
    queryKey: queryKeys.analytics.didUsage(tenantId, params),
    queryFn: () => apiClient.get<DIDUsage[]>(`tenants/${tenantId}/analytics/did-usage`, params),
    enabled: !!tenantId,
  })
}

export function useDurationDistribution(filters: AnalyticsFilters = {}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const params = buildParams(filters)
  return useQuery({
    queryKey: queryKeys.analytics.durationDistribution(tenantId, params),
    queryFn: () => apiClient.get<DurationBucket[]>(`tenants/${tenantId}/analytics/duration-distribution`, params),
    enabled: !!tenantId,
  })
}

export function useTopCallers(filters: AnalyticsFilters = {}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const params = buildParams(filters)
  return useQuery({
    queryKey: queryKeys.analytics.topCallers(tenantId, params),
    queryFn: () => apiClient.get<TopCaller[]>(`tenants/${tenantId}/analytics/top-callers`, params),
    enabled: !!tenantId,
  })
}

export function useHourlyDistribution(filters: AnalyticsFilters = {}) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const params = buildParams(filters)
  return useQuery({
    queryKey: queryKeys.analytics.hourlyDistribution(tenantId, params),
    queryFn: () => apiClient.get<HourlyDistributionPoint[]>(`tenants/${tenantId}/analytics/hourly-distribution`, params),
    enabled: !!tenantId,
  })
}

export function useMSPOverview() {
  return useQuery({
    queryKey: queryKeys.analytics.mspOverview(),
    queryFn: () => apiClient.get<MSPOverviewResponse>("analytics/msp-overview"),
  })
}
