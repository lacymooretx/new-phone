import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

export interface Device {
  id: string
  tenant_id: string
  mac_address: string
  phone_model_id: string
  extension_id: string | null
  name: string | null
  location: string | null
  notes: string | null
  last_provisioned_at: string | null
  last_config_hash: string | null
  provisioning_enabled: boolean
  is_active: boolean
  deactivated_at: string | null
  created_at: string
  updated_at: string
  phone_model_name: string | null
  phone_model_manufacturer: string | null
  extension_number: string | null
}

export interface DeviceCreate {
  mac_address: string
  phone_model_id: string
  extension_id?: string | null
  name?: string | null
  location?: string | null
  notes?: string | null
  provisioning_enabled?: boolean
}

export interface DeviceKey {
  id: string
  device_id: string
  key_section: string
  key_index: number
  key_type: string
  label: string | null
  value: string | null
  line: number
  created_at: string
  updated_at: string
}

export interface DeviceKeyCreate {
  key_section: string
  key_index: number
  key_type: string
  label?: string | null
  value?: string | null
  line?: number
}

export function useDevices() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.devices.list(tenantId),
    queryFn: () => apiClient.get<Device[]>(`tenants/${tenantId}/devices`),
    enabled: !!tenantId,
  })
}

export function useCreateDevice() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: DeviceCreate) =>
      apiClient.post<Device>(`tenants/${tenantId}/devices`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.devices.all(tenantId) }),
  })
}

export function useUpdateDevice() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<DeviceCreate>) =>
      apiClient.patch<Device>(`tenants/${tenantId}/devices/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.devices.all(tenantId) }),
  })
}

export function useDeleteDevice() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/devices/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.devices.all(tenantId) }),
  })
}

export function useDeviceKeys(deviceId: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.devices.keys(tenantId, deviceId),
    queryFn: () => apiClient.get<DeviceKey[]>(`tenants/${tenantId}/devices/${deviceId}/keys`),
    enabled: !!tenantId && !!deviceId,
  })
}

export function useUpdateDeviceKeys() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ deviceId, keys }: { deviceId: string; keys: DeviceKeyCreate[] }) =>
      apiClient.put<DeviceKey[]>(`tenants/${tenantId}/devices/${deviceId}/keys`, { keys }),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: queryKeys.devices.keys(tenantId, variables.deviceId) })
      qc.invalidateQueries({ queryKey: queryKeys.devices.all(tenantId) })
    },
  })
}
