import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

export interface Room {
  id: string
  tenant_id: string
  room_number: string
  extension_id: string | null
  floor: string | null
  room_type: string | null
  status: string
  housekeeping_status: string
  guest_name: string | null
  guest_checkout_at: string | null
  wake_up_time: string | null
  wake_up_enabled: boolean
  restricted_dialing: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export interface RoomCreate {
  room_number: string
  extension_id?: string | null
  floor?: string | null
  room_type?: string | null
  status?: string
  housekeeping_status?: string
  guest_name?: string | null
  guest_checkout_at?: string | null
  wake_up_time?: string | null
  wake_up_enabled?: boolean
  restricted_dialing?: boolean
  notes?: string | null
}

export interface WakeUpCall {
  id: string
  tenant_id: string
  room_id: string
  scheduled_time: string
  status: string
  attempt_count: number
  created_at: string
  updated_at: string
}

export function useRooms(status?: string, floor?: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.hospitality.rooms(tenantId, status, floor),
    queryFn: () => {
      const params = new URLSearchParams()
      if (status) params.set("room_status", status)
      if (floor) params.set("floor", floor)
      const qs = params.toString()
      return apiClient.get<Room[]>(
        `tenants/${tenantId}/hospitality/rooms${qs ? `?${qs}` : ""}`
      )
    },
    enabled: !!tenantId,
  })
}

export function useRoom(roomId: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.hospitality.roomDetail(tenantId, roomId),
    queryFn: () =>
      apiClient.get<Room>(`tenants/${tenantId}/hospitality/rooms/${roomId}`),
    enabled: !!tenantId && !!roomId,
  })
}

export function useCreateRoom() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: RoomCreate) =>
      apiClient.post<Room>(`tenants/${tenantId}/hospitality/rooms`, data),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.hospitality.all(tenantId),
      }),
  })
}

export function useUpdateRoom() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<RoomCreate>) =>
      apiClient.patch<Room>(
        `tenants/${tenantId}/hospitality/rooms/${id}`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.hospitality.all(tenantId),
      }),
  })
}

export function useCheckIn() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      roomId,
      guestName,
      guestCheckoutAt,
    }: {
      roomId: string
      guestName: string
      guestCheckoutAt?: string
    }) =>
      apiClient.post<Room>(
        `tenants/${tenantId}/hospitality/rooms/${roomId}/check-in`,
        {
          guest_name: guestName,
          guest_checkout_at: guestCheckoutAt,
        }
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.hospitality.all(tenantId),
      }),
  })
}

export function useCheckOut() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (roomId: string) =>
      apiClient.post<Room>(
        `tenants/${tenantId}/hospitality/rooms/${roomId}/check-out`,
        {}
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.hospitality.all(tenantId),
      }),
  })
}

export function useWakeUpCalls(roomId: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.hospitality.wakeUpCalls(tenantId, roomId),
    queryFn: () =>
      apiClient.get<WakeUpCall[]>(
        `tenants/${tenantId}/hospitality/rooms/${roomId}/wake-up-calls`
      ),
    enabled: !!tenantId && !!roomId,
  })
}

export function useCreateWakeUpCall() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      roomId,
      scheduledTime,
    }: {
      roomId: string
      scheduledTime: string
    }) =>
      apiClient.post<WakeUpCall>(
        `tenants/${tenantId}/hospitality/rooms/${roomId}/wake-up-calls`,
        { scheduled_time: scheduledTime }
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.hospitality.all(tenantId),
      }),
  })
}

export function useCancelWakeUpCall() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (wakeUpId: string) =>
      apiClient.post<WakeUpCall>(
        `tenants/${tenantId}/hospitality/wake-up-calls/${wakeUpId}/cancel`,
        {}
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: queryKeys.hospitality.all(tenantId),
      }),
  })
}
