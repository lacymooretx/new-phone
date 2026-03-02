import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

// Types matching backend HolidayEntryResponse / HolidayCalendarResponse
export interface HolidayCalendarEntry {
  id: string
  calendar_id: string
  name: string
  date: string
  recur_annually: boolean
  all_day: boolean
  start_time: string | null
  end_time: string | null
}

export interface HolidayCalendar {
  id: string
  tenant_id: string
  name: string
  description: string | null
  entries: HolidayCalendarEntry[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface HolidayEntryCreate {
  name: string
  date: string
  recur_annually?: boolean
  all_day?: boolean
  start_time?: string | null
  end_time?: string | null
}

export interface HolidayCalendarCreate {
  name: string
  description?: string | null
  entries?: HolidayEntryCreate[]
}

export function useHolidayCalendars() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.holidayCalendars.list(tenantId),
    queryFn: () => apiClient.get<HolidayCalendar[]>(`tenants/${tenantId}/holiday-calendars`),
    enabled: !!tenantId,
  })
}

export function useCreateHolidayCalendar() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: HolidayCalendarCreate) =>
      apiClient.post<HolidayCalendar>(`tenants/${tenantId}/holiday-calendars`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.holidayCalendars.all(tenantId) }),
  })
}

export function useUpdateHolidayCalendar() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<HolidayCalendarCreate>) =>
      apiClient.patch<HolidayCalendar>(`tenants/${tenantId}/holiday-calendars/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.holidayCalendars.all(tenantId) }),
  })
}

export function useDeleteHolidayCalendar() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/holiday-calendars/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.holidayCalendars.all(tenantId) }),
  })
}
