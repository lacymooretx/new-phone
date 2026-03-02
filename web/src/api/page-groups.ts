import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// Types matching backend PageGroupMemberResponse / PageGroupResponse
export interface PageGroupMember {
  id: string
  page_group_id: string
  extension_id: string
  position: number
}

export interface PageGroup {
  id: string
  tenant_id: string
  name: string
  page_number: string
  description: string | null
  page_mode: string
  timeout: number
  members: PageGroupMember[]
  site_id: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface PageGroupMemberCreate {
  extension_id: string
  position?: number
}

export interface PageGroupCreate {
  name: string
  page_number: string
  description?: string | null
  page_mode?: string
  timeout?: number
  members?: PageGroupMemberCreate[]
  site_id?: string | null
}

export function usePageGroups() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.pageGroups.list(tenantId),
    queryFn: () => apiClient.get<PageGroup[]>(`tenants/${tenantId}/page-groups`),
    enabled: !!tenantId,
  })
}

export function useCreatePageGroup() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: PageGroupCreate) =>
      apiClient.post<PageGroup>(`tenants/${tenantId}/page-groups`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.pageGroups.all(tenantId) }),
  })
}

export function useUpdatePageGroup() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<PageGroupCreate>) =>
      apiClient.patch<PageGroup>(`tenants/${tenantId}/page-groups/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.pageGroups.all(tenantId) }),
  })
}

export function useDeletePageGroup() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/page-groups/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.pageGroups.all(tenantId) }),
  })
}
