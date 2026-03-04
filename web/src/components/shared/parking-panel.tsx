import { useState, useEffect, useMemo } from "react"
import { ParkingSquare, ArrowDownToLine } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useParkingLots, useAllSlotStates, type SlotState } from "@/api/parking"

function ParkedDuration({ parkedAt }: { parkedAt: string }) {
  const [elapsed, setElapsed] = useState("")
  useEffect(() => {
    const start = new Date(parkedAt).getTime()
    const tick = () => {
      const s = Math.floor((Date.now() - start) / 1000)
      const m = Math.floor(s / 60)
      setElapsed(`${m}:${String(s % 60).padStart(2, "0")}`)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [parkedAt])
  return <span className="font-mono text-xs tabular-nums">{elapsed}</span>
}

export function ParkingPanel({
  onPickup,
  className,
}: {
  onPickup?: (slotNumber: number) => void
  className?: string
}) {
  const { data: lots } = useParkingLots()
  const { data: slots } = useAllSlotStates()
  const occupiedSlots = useMemo(
    () => (slots ?? []).filter((s: SlotState) => s.occupied),
    [slots]
  )

  return (
    <div className={cn("flex flex-col rounded-lg border bg-card", className)}>
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <ParkingSquare className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Parking
        </span>
        {occupiedSlots.length > 0 && (
          <Badge variant="secondary" className="ml-auto h-4 min-w-[18px] px-1 text-[10px] font-mono">
            {occupiedSlots.length}
          </Badge>
        )}
      </div>
      <div className="flex-1 overflow-auto">
        {occupiedSlots.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-6 text-muted-foreground">
            <ParkingSquare className="mb-2 h-5 w-5 opacity-40" />
            <span className="text-xs">No parked calls</span>
            <span className="mt-1 text-[10px] opacity-60">{lots?.length ?? 0} lots configured</span>
          </div>
        ) : (
          <div className="divide-y">
            {occupiedSlots.map((slot: SlotState) => (
              <div key={slot.slot_number} className="flex items-center gap-2 px-3 py-2">
                <div className="flex h-6 w-6 items-center justify-center rounded bg-emerald-500/10 text-emerald-500">
                  <span className="font-mono text-[10px] font-bold">{slot.slot_number}</span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-xs font-medium">
                    {slot.caller_id_name || slot.caller_id_number || "Unknown"}
                  </div>
                  {slot.caller_id_name && slot.caller_id_number && (
                    <div className="truncate text-[10px] text-muted-foreground font-mono">
                      {slot.caller_id_number}
                    </div>
                  )}
                </div>
                {slot.parked_at && (
                  <div className="text-muted-foreground">
                    <ParkedDuration parkedAt={slot.parked_at} />
                  </div>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 shrink-0"
                  onClick={() => onPickup?.(slot.slot_number)}
                >
                  <ArrowDownToLine className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
