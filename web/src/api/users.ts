import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"
import type { Role } from "@/lib/constants"

export interface User {
  id: string
  tenant_id: string
  email: string
  first_name: string
  last_name: string
  role: string
  is_active: boolean
  mfa_enabled: boolean
  last_login_at: string | null
  created_at: string
  updated_at: string
}

export interface UserCreate {
  email: string
  password: string
  first_name: string
  last_name: string
  role?: Role
}

export interface UserUpdate {
  email?: string
  first_name?: string
  last_name?: string
  role?: Role
  is_active?: boolean
}

export function useUsers() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.users.list(tenantId),
    queryFn: () => apiClient.get<User[]>(`tenants/${tenantId}/users`),
    enabled: !!tenantId,
  })
}

export function useCreateUser() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: UserCreate) =>
      apiClient.post<User>(`tenants/${tenantId}/users`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.users.all(tenantId) }),
  })
}

export function useUpdateUser() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & UserUpdate) =>
      apiClient.patch<User>(`tenants/${tenantId}/users/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.users.all(tenantId) }),
  })
}

export function useDeleteUser() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.users.all(tenantId) }),
  })
}
