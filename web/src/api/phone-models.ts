import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "./query-keys"

export interface PhoneModel {
  id: string
  manufacturer: string
  model_name: string
  model_family: string
  max_line_keys: number
  max_expansion_keys: number
  max_expansion_modules: number
  has_color_screen: boolean
  has_wifi: boolean
  has_bluetooth: boolean
  has_expansion_port: boolean
  has_poe: boolean
  has_gigabit: boolean
  firmware_pattern: string | null
  notes: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export function usePhoneModels() {
  return useQuery({
    queryKey: queryKeys.phoneModels.list(),
    queryFn: () => apiClient.get<PhoneModel[]>("phone-models"),
  })
}
