import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

export type PortRequestStatus =
  | "submitted"
  | "pending_loa"
  | "loa_submitted"
  | "foc_received"
  | "in_progress"
  | "completed"
  | "rejected"
  | "cancelled"

export interface PortRequest {
  id: string
  tenant_id: string
  numbers: string[]
  current_carrier: string
  provider: string
  status: PortRequestStatus
  requested_date: string | null
  foc_date: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface PortRequestCreate {
  numbers: string[]
  current_carrier: string
  provider: string
  requested_date?: string | null
  notes?: string | null
}

export interface PortRequestHistory {
  id: string
  port_request_id: string
  status: PortRequestStatus
  message: string | null
  created_at: string
  created_by: string | null
}

export function usePortRequests() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.portRequests.list(tenantId),
    queryFn: () => apiClient.get<PortRequest[]>(`tenants/${tenantId}/port-requests`),
    enabled: !!tenantId,
  })
}

export function usePortRequest(id: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.portRequests.detail(tenantId, id),
    queryFn: () => apiClient.get<PortRequest>(`tenants/${tenantId}/port-requests/${id}`),
    enabled: !!tenantId && !!id,
  })
}

export function usePortRequestHistory(id: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.portRequests.history(tenantId, id),
    queryFn: () => apiClient.get<PortRequestHistory[]>(`tenants/${tenantId}/port-requests/${id}/history`),
    enabled: !!tenantId && !!id,
  })
}

export function useCreatePortRequest() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: PortRequestCreate) =>
      apiClient.post<PortRequest>(`tenants/${tenantId}/port-requests`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.portRequests.all(tenantId) }),
  })
}

export function useUpdatePortRequest() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<PortRequestCreate>) =>
      apiClient.patch<PortRequest>(`tenants/${tenantId}/port-requests/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.portRequests.all(tenantId) }),
  })
}

export function useUploadLoa() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, file }: { id: string; file: File }) => {
      const { accessToken } = useAuthStore.getState()
      const formData = new FormData()
      formData.append("file", file)
      const res = await fetch(
        `/api/v1/tenants/${tenantId}/port-requests/${id}/loa`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${accessToken}` },
          body: formData,
        }
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || res.statusText)
      }
      return res.json()
    },
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: queryKeys.portRequests.detail(tenantId, id) })
      qc.invalidateQueries({ queryKey: queryKeys.portRequests.history(tenantId, id) })
    },
  })
}

export function useCheckPortStatus() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.post<PortRequest>(`tenants/${tenantId}/port-requests/${id}/check-status`),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: queryKeys.portRequests.detail(tenantId, id) })
      qc.invalidateQueries({ queryKey: queryKeys.portRequests.list(tenantId) })
    },
  })
}

export function useCancelPortRequest() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.post<void>(`tenants/${tenantId}/port-requests/${id}/cancel`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.portRequests.all(tenantId) }),
  })
}

export function useCompletePortRequest() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.post<void>(`tenants/${tenantId}/port-requests/${id}/complete`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.portRequests.all(tenantId) }),
  })
}
