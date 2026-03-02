import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "./query-keys"

export interface ParkingLot {
  id: string
  tenant_id: string
  name: string
  lot_number: number
  slot_start: number
  slot_end: number
  timeout_seconds: number
  comeback_enabled: boolean
  comeback_extension: string | null
  moh_prompt_id: string | null
  site_id: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ParkingLotCreate {
  name: string
  lot_number: number
  slot_start: number
  slot_end: number
  timeout_seconds?: number
  comeback_enabled?: boolean
  comeback_extension?: string | null
  moh_prompt_id?: string | null
  site_id?: string | null
}

export interface SlotState {
  slot_number: number
  occupied: boolean
  caller_id_number: string | null
  caller_id_name: string | null
  parked_at: string | null
  parked_by: string | null
  lot_name: string | null
  lot_id: string | null
}

export function useParkingLots() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.parkingLots.list(tenantId),
    queryFn: () => apiClient.get<ParkingLot[]>(`tenants/${tenantId}/parking-lots`),
    enabled: !!tenantId,
  })
}

export function useCreateParkingLot() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ParkingLotCreate) =>
      apiClient.post<ParkingLot>(`tenants/${tenantId}/parking-lots`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.parkingLots.all(tenantId) }),
  })
}

export function useUpdateParkingLot() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<ParkingLotCreate>) =>
      apiClient.patch<ParkingLot>(`tenants/${tenantId}/parking-lots/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.parkingLots.all(tenantId) }),
  })
}

export function useDeleteParkingLot() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`tenants/${tenantId}/parking-lots/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.parkingLots.all(tenantId) }),
  })
}

export function useAllSlotStates() {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.parkingLots.slots(tenantId),
    queryFn: () => apiClient.get<SlotState[]>(`tenants/${tenantId}/parking-lots/slots`),
    enabled: !!tenantId,
    staleTime: 60_000,
  })
}

export function useLotSlotStates(lotId: string) {
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  return useQuery({
    queryKey: queryKeys.parkingLots.lotSlots(tenantId, lotId),
    queryFn: () => apiClient.get<SlotState[]>(`tenants/${tenantId}/parking-lots/${lotId}/slots`),
    enabled: !!tenantId && !!lotId,
    staleTime: 60_000,
  })
}
