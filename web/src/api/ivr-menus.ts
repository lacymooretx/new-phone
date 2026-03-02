import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// Types matching backend IVRMenuOptionResponse / IVRMenuResponse
export interface IVRMenuOption {
  id: string
  ivr_menu_id: string
  digits: string
  action_type: string
  action_target_id: string | null
  action_target_value: string | null
  label: string | null
  position: number
}

export interface IVRMenu {
  id: string
  tenant_id: string
  name: string
  description: string | null
  greet_long_prompt_id: string | null
  greet_short_prompt_id: string | null
  invalid_sound_prompt_id: string | null
  exit_sound_prompt_id: string | null
  timeout: number
  inter_digit_timeout: number
  max_failures: number
  max_timeouts: number
  digit_len: number
  exit_destination_type: string | null
  exit_destination_id: string | null
  tts_engine: string | null
  tts_voice: string | null
  enabled: boolean
  is_active: boolean
  options: IVRMenuOption[]
  created_at: string
  updated_at: string
}

export interface IVRMenuOptionCreate {
  digits: string
  action_type: string
  action_target_id?: string | null
  action_target_value?: string | null
  label?: string | null
  position?: number
}

export interface IVRMenuCreate {
  name: string
  description?: string | null
  greet_long_prompt_id?: string | null
  greet_short_prompt_id?: string | null
  invalid_sound_prompt_id?: string | null
  exit_sound_prompt_id?: string | null
  timeout?: number
  inter_digit_timeout?: number
  max_failures?: number
  max_timeouts?: number
  digit_len?: number
  exit_destination_type?: string | null
  exit_destination_id?: string | null
  enabled?: boolean
  options?: IVRMenuOptionCreate[]
}

export function useIvrMenus() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.ivrMenus.list(tenantId),
    queryFn: () => apiClient.get<IVRMenu[]>(`tenants/${tenantId}/ivr-menus`),
    enabled: !!tenantId,
  })
}

export function useCreateIvrMenu() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: IVRMenuCreate) =>
      apiClient.post<IVRMenu>(`tenants/${tenantId}/ivr-menus`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.ivrMenus.all(tenantId) }),
  })
}

export function useUpdateIvrMenu() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<IVRMenuCreate>) =>
      apiClient.patch<IVRMenu>(`tenants/${tenantId}/ivr-menus/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.ivrMenus.all(tenantId) }),
  })
}

export function useDeleteIvrMenu() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/ivr-menus/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.ivrMenus.all(tenantId) }),
  })
}
