import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// ── Types ──────────────────────────────────────────────────────────

export interface TelephonyProviderConfig {
  id: string
  tenant_id: string | null
  provider_type: string
  label: string
  is_default: boolean
  is_active: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export interface TelephonyProviderConfigCreate {
  provider_type: "clearlyip" | "twilio"
  label: string
  credentials: Record<string, string>
  is_default?: boolean
  notes?: string | null
}

export interface TelephonyProviderConfigUpdate {
  label?: string
  credentials?: Record<string, string>
  is_default?: boolean
  is_active?: boolean
  notes?: string | null
}

export interface TelephonyProviderEffective {
  provider_type: string
  source: "tenant" | "msp" | "env_var" | "none"
  is_configured: boolean
  label: string | null
  config_id: string | null
}

// ── MSP / Platform hooks ───────────────────────────────────────────

export function usePlatformTelephonyProviders() {
  return useQuery({
    queryKey: queryKeys.telephonyProviders.platform(),
    queryFn: () =>
      apiClient.get<TelephonyProviderConfig[]>("platform/telephony-providers"),
  })
}

export function useCreatePlatformTelephonyProvider() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TelephonyProviderConfigCreate) =>
      apiClient.post<TelephonyProviderConfig>(
        "platform/telephony-providers",
        data,
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.telephonyProviders.platform(),
      }),
  })
}

export function useUpdatePlatformTelephonyProvider() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      ...data
    }: { id: string } & TelephonyProviderConfigUpdate) =>
      apiClient.patch<TelephonyProviderConfig>(
        `platform/telephony-providers/${id}`,
        data,
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.telephonyProviders.platform(),
      }),
  })
}

export function useDeletePlatformTelephonyProvider() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`platform/telephony-providers/${id}`),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.telephonyProviders.platform(),
      }),
  })
}

// ── Tenant hooks ───────────────────────────────────────────────────

export function useTenantTelephonyProviders(tenantId?: string) {
  const activeTenantId = useAuthStore((s) => s.activeTenantId)
  const tid = tenantId ?? activeTenantId
  return useQuery({
    queryKey: queryKeys.telephonyProviders.tenant(tid!),
    queryFn: () =>
      apiClient.get<TelephonyProviderConfig[]>(
        `tenants/${tid}/telephony-providers`,
      ),
    enabled: !!tid,
  })
}

export function useTenantEffectiveProviders(tenantId?: string) {
  const activeTenantId = useAuthStore((s) => s.activeTenantId)
  const tid = tenantId ?? activeTenantId
  return useQuery({
    queryKey: queryKeys.telephonyProviders.effective(tid!),
    queryFn: () =>
      apiClient.get<TelephonyProviderEffective[]>(
        `tenants/${tid}/telephony-providers/effective`,
      ),
    enabled: !!tid,
  })
}

export function useCreateTenantTelephonyProvider() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TelephonyProviderConfigCreate) =>
      apiClient.post<TelephonyProviderConfig>(
        `tenants/${tenantId}/telephony-providers`,
        data,
      ),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.telephonyProviders.tenant(tenantId),
      })
      qc.invalidateQueries({
        queryKey: queryKeys.telephonyProviders.effective(tenantId),
      })
    },
  })
}

export function useUpdateTenantTelephonyProvider() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      ...data
    }: { id: string } & TelephonyProviderConfigUpdate) =>
      apiClient.patch<TelephonyProviderConfig>(
        `tenants/${tenantId}/telephony-providers/${id}`,
        data,
      ),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.telephonyProviders.tenant(tenantId),
      })
      qc.invalidateQueries({
        queryKey: queryKeys.telephonyProviders.effective(tenantId),
      })
    },
  })
}

export function useDeleteTenantTelephonyProvider() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/telephony-providers/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: queryKeys.telephonyProviders.tenant(tenantId),
      })
      qc.invalidateQueries({
        queryKey: queryKeys.telephonyProviders.effective(tenantId),
      })
    },
  })
}
