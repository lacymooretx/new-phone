import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// Types matching backend SIPTrunkResponse
export interface SIPTrunk {
  id: string
  tenant_id: string
  name: string
  auth_type: string
  host: string
  port: number
  username: string | null
  ip_acl: string | null
  codec_preferences: Record<string, unknown> | null
  max_channels: number
  transport: string
  inbound_cid_mode: string
  failover_trunk_id: string | null
  notes: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

// Note: password is write-only (never returned in response)
export interface SIPTrunkCreate {
  name: string
  auth_type: string
  host: string
  port?: number
  username?: string | null
  password?: string | null
  ip_acl?: string | null
  codec_preferences?: Record<string, unknown> | null
  max_channels?: number
  transport?: string
  inbound_cid_mode?: string
  failover_trunk_id?: string | null
  notes?: string | null
}

export function useSipTrunks() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.sipTrunks.list(tenantId),
    queryFn: () => apiClient.get<SIPTrunk[]>(`tenants/${tenantId}/trunks`),
    enabled: !!tenantId,
  })
}

export function useCreateSipTrunk() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: SIPTrunkCreate) =>
      apiClient.post<SIPTrunk>(`tenants/${tenantId}/trunks`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.sipTrunks.all(tenantId) }),
  })
}

export function useUpdateSipTrunk() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<SIPTrunkCreate>) =>
      apiClient.patch<SIPTrunk>(`tenants/${tenantId}/trunks/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.sipTrunks.all(tenantId) }),
  })
}

export function useDeleteSipTrunk() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/trunks/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.sipTrunks.all(tenantId) }),
  })
}

// --- Provider operations ---

export interface TrunkProvisionRequest {
  provider: "clearlyip" | "twilio"
  name: string
  region: string
  channels?: number
  config?: Record<string, unknown>
}

export interface TrunkTestResult {
  status: "ok" | "error"
  latency_ms: number | null
  message: string
}

export function useProvisionTrunk() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TrunkProvisionRequest) =>
      apiClient.post<SIPTrunk>(`tenants/${tenantId}/trunks/provision`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.sipTrunks.all(tenantId) }),
  })
}

export function useDeprovisionTrunk() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.post<void>(`tenants/${tenantId}/trunks/${id}/deprovision`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.sipTrunks.all(tenantId) }),
  })
}

export function useTestTrunk() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.post<TrunkTestResult>(`tenants/${tenantId}/trunks/${id}/test`),
  })
}

// --- ClearlyIP keycode activation ---

export interface KeycodeActivateRequest {
  keycode: string
  name_prefix?: string
  import_dids?: boolean
}

export interface KeycodeActivateResult {
  primary_trunk_id: string
  secondary_trunk_id: string | null
  imported_dids: string[]
  location_name: string
}

export interface KeycodeRefreshResult {
  trunks_updated: number
  dids_added: string[]
  dids_removed: string[]
  credentials_changed: boolean
}

export function useActivateKeycode() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: KeycodeActivateRequest) =>
      apiClient.post<KeycodeActivateResult>(`tenants/${tenantId}/trunks/activate-keycode`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.sipTrunks.all(tenantId) })
      qc.invalidateQueries({ queryKey: queryKeys.dids.all(tenantId) })
    },
  })
}

export function useRefreshClearlyip() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiClient.post<KeycodeRefreshResult>(`tenants/${tenantId}/trunks/refresh-clearlyip`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.sipTrunks.all(tenantId) })
      qc.invalidateQueries({ queryKey: queryKeys.dids.all(tenantId) })
    },
  })
}
