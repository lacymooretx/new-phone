import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// ── Types ──

export interface DispositionCode {
  id: string
  list_id: string
  code: string
  label: string
  category: string | null
  position: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface DispositionCodeList {
  id: string
  tenant_id: string
  name: string
  description: string | null
  is_active: boolean
  codes: DispositionCode[]
  created_at: string
  updated_at: string
}

export interface DispositionCodeListCreate {
  name: string
  description?: string | null
}

export interface DispositionCodeCreate {
  code: string
  label: string
  category?: string | null
  position?: number
}

export interface DispositionCodeUpdate {
  code?: string
  label?: string
  category?: string | null
  position?: number
  is_active?: boolean
}

// ── List hooks ──

export function useDispositionCodeLists() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.dispositionCodeLists.list(tenantId),
    queryFn: () =>
      apiClient.get<DispositionCodeList[]>(
        `tenants/${tenantId}/disposition-code-lists`
      ),
    enabled: !!tenantId,
  })
}

export function useDispositionCodeList(listId: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.dispositionCodeLists.detail(tenantId, listId),
    queryFn: () =>
      apiClient.get<DispositionCodeList>(
        `tenants/${tenantId}/disposition-code-lists/${listId}`
      ),
    enabled: !!tenantId && !!listId,
  })
}

export function useCreateCodeList() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: DispositionCodeListCreate) =>
      apiClient.post<DispositionCodeList>(
        `tenants/${tenantId}/disposition-code-lists`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.dispositionCodeLists.all(tenantId),
      }),
  })
}

export function useUpdateCodeList() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      ...data
    }: { id: string } & Partial<DispositionCodeListCreate> & {
      is_active?: boolean
    }) =>
      apiClient.patch<DispositionCodeList>(
        `tenants/${tenantId}/disposition-code-lists/${id}`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.dispositionCodeLists.all(tenantId),
      }),
  })
}

export function useDeleteCodeList() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/disposition-code-lists/${id}`),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.dispositionCodeLists.all(tenantId),
      }),
  })
}

// ── Code hooks ──

export function useCreateCode() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      listId,
      ...data
    }: DispositionCodeCreate & { listId: string }) =>
      apiClient.post<DispositionCode>(
        `tenants/${tenantId}/disposition-code-lists/${listId}/codes`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.dispositionCodeLists.all(tenantId),
      }),
  })
}

export function useUpdateCode() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      listId,
      codeId,
      ...data
    }: DispositionCodeUpdate & { listId: string; codeId: string }) =>
      apiClient.patch<DispositionCode>(
        `tenants/${tenantId}/disposition-code-lists/${listId}/codes/${codeId}`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.dispositionCodeLists.all(tenantId),
      }),
  })
}

export function useDeleteCode() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ listId, codeId }: { listId: string; codeId: string }) =>
      apiClient.delete(
        `tenants/${tenantId}/disposition-code-lists/${listId}/codes/${codeId}`
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.dispositionCodeLists.all(tenantId),
      }),
  })
}
