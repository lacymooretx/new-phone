import { useState, useEffect, useMemo, useCallback } from "react"
import { useExtensions } from "@/api/extensions"
import { useParkingLots, useAllSlotStates, type SlotState } from "@/api/parking"
import { useQueueStats } from "@/api/queues"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  Phone,
  PhoneOff,
  ParkingSquare,
  Search,
  Users,
  Headset,
  Clock,
  Star,
  CircleDot,
  ArrowDownToLine,
} from "lucide-react"
import { cn } from "@/lib/utils"

// ── Live Clock ──────────────────────────────────────────────────────
function LiveClock() {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return (
    <span className="font-mono text-xs tabular-nums text-muted-foreground">
      {now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
    </span>
  )
}

// ── Parked Call Duration ─────────────────────────────────────────────
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

// ── Extension Status Logic ──────────────────────────────────────────
type ExtStatus = "available" | "busy" | "ringing" | "dnd" | "offline"

function getExtensionStatus(ext: {
  is_active: boolean
  dnd_enabled: boolean
  agent_status: string | null
}): ExtStatus {
  if (!ext.is_active) return "offline"
  if (ext.dnd_enabled) return "dnd"
  if (ext.agent_status === "On Break" || ext.agent_status === "Logged Out") return "offline"
  if (ext.agent_status === "On Call" || ext.agent_status === "In a Queue Call") return "busy"
  if (ext.agent_status === "Available" || ext.agent_status === "Waiting") return "available"
  // Default: if active and not DND, assume available
  return "available"
}

const STATUS_CONFIG: Record<ExtStatus, { dot: string; border: string; bg: string; label: string }> = {
  available: {
    dot: "bg-emerald-400",
    border: "border-emerald-500/30",
    bg: "bg-emerald-500/5 hover:bg-emerald-500/10",
    label: "Available",
  },
  busy: {
    dot: "bg-red-400",
    border: "border-red-500/30",
    bg: "bg-red-500/5 hover:bg-red-500/10",
    label: "On Call",
  },
  ringing: {
    dot: "bg-amber-400 animate-pulse",
    border: "border-amber-500/40",
    bg: "bg-amber-500/5 hover:bg-amber-500/10",
    label: "Ringing",
  },
  dnd: {
    dot: "bg-zinc-400",
    border: "border-zinc-500/20",
    bg: "bg-zinc-500/5 hover:bg-zinc-500/8 opacity-60",
    label: "DND",
  },
  offline: {
    dot: "bg-zinc-600",
    border: "border-zinc-700/20",
    bg: "bg-zinc-800/5 hover:bg-zinc-500/5 opacity-40",
    label: "Offline",
  },
}

// ── Extension Tile ──────────────────────────────────────────────────
function ExtensionTile({
  extensionNumber,
  name,
  status,
  onClick,
}: {
  extensionNumber: string
  name: string
  status: ExtStatus
  onClick?: () => void
}) {
  const cfg = STATUS_CONFIG[status]
  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={onClick}
            className={cn(
              "relative flex flex-col items-center justify-center rounded-md border px-1 py-1.5",
              "transition-all duration-150 cursor-pointer select-none",
              "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
              cfg.border,
              cfg.bg
            )}
          >
            <div className={cn("absolute top-1 right-1 h-1.5 w-1.5 rounded-full", cfg.dot)} />
            <span className="font-mono text-[11px] font-semibold leading-none tracking-tight">
              {extensionNumber}
            </span>
            <span className="mt-0.5 max-w-full truncate text-[9px] leading-none text-muted-foreground">
              {name || extensionNumber}
            </span>
          </button>
        </TooltipTrigger>
        <TooltipContent side="top" className="text-xs">
          <div className="font-medium">{name || extensionNumber}</div>
          <div className="text-muted-foreground">Ext {extensionNumber} — {cfg.label}</div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

// ── Panel Shell ─────────────────────────────────────────────────────
function Panel({
  title,
  icon: Icon,
  badge,
  children,
  className,
}: {
  title: string
  icon: React.ElementType
  badge?: number | string
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn("flex flex-col rounded-lg border bg-card", className)}>
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <Icon className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {title}
        </span>
        {badge != null && (
          <Badge variant="secondary" className="ml-auto h-4 min-w-[18px] px-1 text-[10px] font-mono">
            {badge}
          </Badge>
        )}
      </div>
      <div className="flex-1 overflow-auto">{children}</div>
    </div>
  )
}

// ── Active Calls Panel ──────────────────────────────────────────────
function ActiveCallsPanel() {
  // In a real implementation, this would subscribe to ESL events via WebSocket
  // For now, show the empty state
  return (
    <Panel title="Active Calls" icon={Phone} badge={0}>
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
        <PhoneOff className="mb-2 h-5 w-5 opacity-40" />
        <span className="text-xs">No active calls</span>
      </div>
    </Panel>
  )
}

// ── Parking Panel ───────────────────────────────────────────────────
function ParkingPanel() {
  const { data: lots } = useParkingLots()
  const { data: slots } = useAllSlotStates()
  const occupiedSlots = useMemo(
    () => (slots ?? []).filter((s: SlotState) => s.occupied),
    [slots]
  )

  return (
    <Panel title="Parking" icon={ParkingSquare} badge={occupiedSlots.length || undefined}>
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
              <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0">
                <ArrowDownToLine className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </Panel>
  )
}

// ── Queue Stats Panel ───────────────────────────────────────────────
function QueueStatsPanel() {
  const { data: stats } = useQueueStats()

  if (!stats?.length) {
    return (
      <Panel title="Queues" icon={Headset}>
        <div className="flex flex-col items-center justify-center py-6 text-muted-foreground">
          <Headset className="mb-2 h-5 w-5 opacity-40" />
          <span className="text-xs">No queues</span>
        </div>
      </Panel>
    )
  }

  const totalWaiting = stats.reduce((a, q) => a + q.waiting_count, 0)

  return (
    <Panel title="Queues" icon={Headset} badge={totalWaiting || undefined}>
      <div className="divide-y">
        {stats.map((q) => (
          <div key={q.queue_id} className="px-3 py-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium truncate">{q.queue_name}</span>
              {q.waiting_count > 0 && (
                <Badge variant="destructive" className="h-4 px-1 text-[10px] font-mono">
                  {q.waiting_count} waiting
                </Badge>
              )}
            </div>
            <div className="mt-1 flex gap-3 text-[10px] text-muted-foreground">
              <span className="flex items-center gap-1">
                <Users className="h-2.5 w-2.5" />
                {q.agents_available}/{q.agents_logged_in}
              </span>
              {q.longest_wait_seconds > 0 && (
                <span className="flex items-center gap-1">
                  <Clock className="h-2.5 w-2.5" />
                  {Math.floor(q.longest_wait_seconds / 60)}:{String(q.longest_wait_seconds % 60).padStart(2, "0")}
                </span>
              )}
              {q.agents_on_call > 0 && (
                <span className="flex items-center gap-1">
                  <Phone className="h-2.5 w-2.5" />
                  {q.agents_on_call} on call
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </Panel>
  )
}

// ── Speed Dials Panel ───────────────────────────────────────────────
function SpeedDialsPanel() {
  // Placeholder — would load from user preferences
  const speedDials = [
    { label: "Front Desk", number: "100" },
    { label: "IT Support", number: "200" },
    { label: "Emergency", number: "911" },
  ]

  return (
    <Panel title="Speed Dials" icon={Star}>
      <div className="grid grid-cols-1 gap-1 p-2">
        {speedDials.map((sd) => (
          <button
            key={sd.number}
            className="flex items-center gap-2 rounded-md border border-transparent px-2 py-1.5 text-left transition-colors hover:border-border hover:bg-accent"
          >
            <Phone className="h-3 w-3 text-muted-foreground" />
            <span className="flex-1 text-xs">{sd.label}</span>
            <span className="font-mono text-[10px] text-muted-foreground">{sd.number}</span>
          </button>
        ))}
      </div>
    </Panel>
  )
}

// ── Status Legend ────────────────────────────────────────────────────
function StatusLegend() {
  const items: { status: ExtStatus; label: string }[] = [
    { status: "available", label: "Available" },
    { status: "busy", label: "On Call" },
    { status: "ringing", label: "Ringing" },
    { status: "dnd", label: "DND" },
    { status: "offline", label: "Offline" },
  ]
  return (
    <div className="flex items-center gap-3">
      {items.map(({ status, label }) => (
        <div key={status} className="flex items-center gap-1">
          <div className={cn("h-1.5 w-1.5 rounded-full", STATUS_CONFIG[status].dot)} />
          <span className="text-[10px] text-muted-foreground">{label}</span>
        </div>
      ))}
    </div>
  )
}

// ── Main Page ───────────────────────────────────────────────────────
export function ReceptionistPage() {
  const [search, setSearch] = useState("")
  const { data: extensions, isLoading } = useExtensions()

  const filteredExtensions = useMemo(() => {
    const all = (extensions ?? []).filter((e) => e.is_active)
    if (!search.trim()) return all
    const q = search.toLowerCase()
    return all.filter(
      (e) =>
        e.extension_number.includes(q) ||
        (e.internal_cid_name ?? "").toLowerCase().includes(q)
    )
  }, [extensions, search])

  // Group by status for sorting: available first, then busy, ringing, dnd, offline
  const sortedExtensions = useMemo(() => {
    const order: Record<ExtStatus, number> = { ringing: 0, busy: 1, available: 2, dnd: 3, offline: 4 }
    return [...filteredExtensions].sort((a, b) => {
      const sa = getExtensionStatus(a)
      const sb = getExtensionStatus(b)
      if (order[sa] !== order[sb]) return order[sa] - order[sb]
      return a.extension_number.localeCompare(b.extension_number, undefined, { numeric: true })
    })
  }, [filteredExtensions])

  const statusCounts = useMemo(() => {
    const counts: Record<ExtStatus, number> = { available: 0, busy: 0, ringing: 0, dnd: 0, offline: 0 }
    for (const ext of extensions ?? []) {
      if (!ext.is_active && !ext.dnd_enabled) continue
      counts[getExtensionStatus(ext)]++
    }
    return counts
  }, [extensions])

  const handleTransfer = useCallback((extNumber: string) => {
    // Would integrate with softphone to blind/attended transfer
    console.log("Transfer to:", extNumber)
  }, [])

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col overflow-hidden">
      {/* ── Top Bar ─────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 border-b bg-card px-4 py-2">
        <div className="flex items-center gap-2">
          <CircleDot className="h-4 w-4 text-emerald-500" />
          <span className="text-sm font-semibold tracking-tight">Receptionist Console</span>
        </div>

        <div className="mx-4 h-4 w-px bg-border" />

        {/* Status summary chips */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            <span className="font-mono text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
              {statusCounts.available}
            </span>
          </div>
          <div className="flex items-center gap-1 rounded-full bg-red-500/10 px-2 py-0.5">
            <div className="h-1.5 w-1.5 rounded-full bg-red-400" />
            <span className="font-mono text-[10px] font-medium text-red-600 dark:text-red-400">
              {statusCounts.busy}
            </span>
          </div>
          {statusCounts.ringing > 0 && (
            <div className="flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5">
              <div className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
              <span className="font-mono text-[10px] font-medium text-amber-600 dark:text-amber-400">
                {statusCounts.ringing}
              </span>
            </div>
          )}
        </div>

        <div className="flex-1" />

        {/* Search */}
        <div className="relative w-64">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search extensions..."
            className="h-7 pl-8 text-xs"
          />
        </div>

        <div className="mx-2 h-4 w-px bg-border" />
        <LiveClock />
      </div>

      {/* ── Main Content ────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <div className="flex w-72 shrink-0 flex-col gap-2 overflow-auto border-r bg-muted/30 p-2">
          <ActiveCallsPanel />
          <ParkingPanel />
        </div>

        {/* Center — BLF Grid */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex items-center justify-between border-b px-4 py-1.5">
            <div className="flex items-center gap-2">
              <Users className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Extensions
              </span>
              <span className="font-mono text-[10px] text-muted-foreground">
                ({filteredExtensions.length})
              </span>
            </div>
            <StatusLegend />
          </div>

          <div className="flex-1 overflow-auto p-3">
            {isLoading ? (
              <div className="flex h-full items-center justify-center">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
              </div>
            ) : sortedExtensions.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-muted-foreground">
                <Phone className="mb-2 h-8 w-8 opacity-30" />
                <span className="text-sm">
                  {search ? "No extensions match your search" : "No extensions configured"}
                </span>
              </div>
            ) : (
              <div className="grid grid-cols-[repeat(auto-fill,minmax(72px,1fr))] gap-1.5">
                {sortedExtensions.map((ext) => (
                  <ExtensionTile
                    key={ext.id}
                    extensionNumber={ext.extension_number}
                    name={ext.internal_cid_name ?? ""}
                    status={getExtensionStatus(ext)}
                    onClick={() => handleTransfer(ext.extension_number)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="flex w-72 shrink-0 flex-col gap-2 overflow-auto border-l bg-muted/30 p-2">
          <QueueStatsPanel />
          <SpeedDialsPanel />
        </div>
      </div>
    </div>
  )
}
