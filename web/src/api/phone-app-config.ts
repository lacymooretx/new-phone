import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "./query-keys"

export interface PhoneAppConfig {
  id: string
  tenant_id: string

  // App toggles
  directory_enabled: boolean
  voicemail_enabled: boolean
  call_history_enabled: boolean
  parking_enabled: boolean
  queue_dashboard_enabled: boolean
  settings_enabled: boolean
  page_size: number
  company_name: string | null

  // Phone locale / display
  timezone: string
  language: string
  date_format: string
  time_format: string

  // Security
  has_phone_admin_password: boolean

  // Branding
  logo_url: string | null
  ringtone: string
  backlight_time: number
  screensaver_type: string

  // Firmware
  firmware_url: string | null

  // Codecs
  codec_priority: string

  // Feature codes
  pickup_code: string
  intercom_code: string
  parking_code: string
  dnd_on_code: string | null
  dnd_off_code: string | null
  fwd_unconditional_code: string | null
  fwd_busy_code: string | null
  fwd_noanswer_code: string | null

  // Network / QoS
  dscp_sip: number
  dscp_rtp: number
  vlan_enabled: boolean
  vlan_id: number | null
  vlan_priority: number

  // Action URLs
  action_urls_enabled: boolean

  created_at: string
  updated_at: string
}

export type PhoneAppConfigUpdate = Partial<
  Omit<PhoneAppConfig, "id" | "tenant_id" | "has_phone_admin_password" | "created_at" | "updated_at">
> & {
  phone_admin_password?: string | null
}

export function usePhoneAppConfig(tenantId: string) {
  return useQuery({
    queryKey: queryKeys.phoneAppConfig.detail(tenantId),
    queryFn: () => apiClient.get<PhoneAppConfig>(`/tenants/${tenantId}/devices/phone-app-config`),
  })
}

export function useUpdatePhoneAppConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ tenantId, data }: { tenantId: string; data: PhoneAppConfigUpdate }) =>
      apiClient.patch<PhoneAppConfig>(`/tenants/${tenantId}/devices/phone-app-config`, data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: queryKeys.phoneAppConfig.detail(vars.tenantId) })
    },
  })
}
