import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

export interface UsageRecord {
  id: string
  tenant_id: string
  period_start: string
  period_end: string
  metric: string
  quantity: number
  unit_cost: number | null
  total_cost: number | null
  created_at: string
  updated_at: string
}

export interface RateDeck {
  id: string
  tenant_id: string
  name: string
  description: string | null
  is_default: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface RateDeckEntry {
  id: string
  rate_deck_id: string
  prefix: string
  destination: string
  per_minute_rate: number
  connection_fee: number
  minimum_seconds: number
  created_at: string
  updated_at: string
}

export interface BillingConfig {
  id: string
  tenant_id: string
  billing_provider: string
  connectwise_agreement_id: string | null
  pax8_subscription_id: string | null
  billing_cycle_day: number
  auto_generate: boolean
  created_at: string
  updated_at: string
}

export interface RateDeckCreate {
  name: string
  description?: string
  is_default?: boolean
  is_active?: boolean
}

export interface RateDeckEntryCreate {
  prefix: string
  destination: string
  per_minute_rate: number
  connection_fee?: number
  minimum_seconds?: number
}

export function useUsageRecords(periodStart?: string, periodEnd?: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.billing.usage(tenantId, periodStart, periodEnd),
    queryFn: () => {
      const params: Record<string, string> = {}
      if (periodStart) params.period_start = periodStart
      if (periodEnd) params.period_end = periodEnd
      return apiClient.get<{ items: UsageRecord[]; total: number }>(`tenants/${tenantId}/billing/usage`, params)
    },
    enabled: !!tenantId,
  })
}

export function useRateDecks() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.billing.rateDecks(tenantId),
    queryFn: () => apiClient.get<RateDeck[]>(`tenants/${tenantId}/billing/rate-decks`),
    enabled: !!tenantId,
  })
}

export function useCreateRateDeck() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: RateDeckCreate) => apiClient.post<RateDeck>(`tenants/${tenantId}/billing/rate-decks`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.billing.rateDecks(tenantId) }),
  })
}

export function useBillingConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.billing.config(tenantId),
    queryFn: () => apiClient.get<BillingConfig>(`tenants/${tenantId}/billing/config`),
    enabled: !!tenantId,
  })
}

export function useUpdateBillingConfig() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<BillingConfig>) => apiClient.put<BillingConfig>(`tenants/${tenantId}/billing/config`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.billing.config(tenantId) }),
  })
}
