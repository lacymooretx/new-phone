import { useState, useEffect, useMemo, useCallback, useRef } from "react"
import { useTranslation } from "react-i18next"
import {
  Phone,
  PhoneOff,
  PhoneIncoming,
  PhoneOutgoing,
  Mic,
  MicOff,
  Pause,
  Play,
  ParkingSquare,
  Hash,
  Search,
  Users,
  Headset,
  Clock,
  Voicemail,
  History,
  ArrowRightLeft,
  X,
  Check,
  Building2,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { useSoftphoneStore } from "@/stores/softphone-store"
import { useSoftphoneInit } from "@/hooks/use-softphone-init"
import { useHeadset } from "@/hooks/use-headset"
import { useCallTimer } from "@/hooks/use-call-timer"
import { useExtensions } from "@/api/extensions"
import { useTenantExtensions } from "@/api/tenant-extensions"
import { useTenants } from "@/api/tenants"
import { useCdrs, type CDR } from "@/api/cdrs"
import { useVoicemailBoxes, useVoicemailMessages, type VoicemailMessage } from "@/api/voicemail"
import { useQueueStats } from "@/api/queues"
import { useAuthStore } from "@/stores/auth-store"
import { isMspRole } from "@/lib/constants"
import { type ExtStatus, getExtensionStatus, STATUS_CONFIG } from "@/lib/extension-status"
import { ExtensionTile } from "@/components/shared/extension-tile"
import { ParkingPanel } from "@/components/shared/parking-panel"

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

// ── Dialpad Tab ─────────────────────────────────────────────────────
const KEYS = [
  ["1", "2", "3"],
  ["4", "5", "6"],
  ["7", "8", "9"],
  ["*", "0", "#"],
]

function DialpadTab() {
  const { t } = useTranslation()
  const [number, setNumber] = useState("")
  const { callState, makeCall, sendDTMF } = useSoftphoneStore()
  const inCall = callState === "connected" || callState === "on_hold"

  const handleKey = (key: string) => {
    if (inCall) sendDTMF(key)
    setNumber((prev) => prev + key)
  }

  const handleCall = () => {
    if (!number.trim()) return
    makeCall(number.trim())
    setNumber("")
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault()
      handleCall()
    }
  }

  return (
    <div className="flex flex-col gap-3 p-3">
      <Input
        value={number}
        onChange={(e) => setNumber(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t("softphone.enterNumber")}
        className="text-center text-lg font-mono h-10 bg-background/50"
      />
      <div className="grid grid-cols-3 gap-1.5">
        {KEYS.flat().map((key) => (
          <Button
            key={key}
            variant="outline"
            className="h-11 text-base font-mono hover:bg-accent/80"
            onClick={() => handleKey(key)}
          >
            {key}
          </Button>
        ))}
      </div>
      {!inCall && (
        <Button
          onClick={handleCall}
          disabled={!number.trim() || callState !== "idle"}
          className="h-11 bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
        >
          <Phone className="size-4 mr-2" />
          {t("softphone.call")}
        </Button>
      )}
    </div>
  )
}

// ── Recent Calls Tab ────────────────────────────────────────────────
function RecentTab() {
  const { data: cdrs, isLoading } = useCdrs({ limit: 30 })
  const { makeCall, callState } = useSoftphoneStore()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
      </div>
    )
  }

  if (!cdrs?.length) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <History className="mb-2 h-6 w-6 opacity-40" />
        <span className="text-xs">No recent calls</span>
      </div>
    )
  }

  return (
    <div className="divide-y overflow-auto">
      {cdrs.map((cdr: CDR) => {
        const isInbound = cdr.direction === "inbound"
        const displayNumber = isInbound ? cdr.caller_number : cdr.called_number
        const displayName = isInbound ? cdr.caller_name : ""
        const duration = cdr.duration_seconds
        const mins = Math.floor(duration / 60)
        const secs = duration % 60

        return (
          <button
            key={cdr.id}
            className="flex items-center gap-2.5 px-3 py-2.5 w-full text-left hover:bg-accent/50 transition-colors"
            onClick={() => callState === "idle" && makeCall(displayNumber)}
          >
            <div className={cn(
              "flex items-center justify-center h-7 w-7 rounded-full shrink-0",
              isInbound ? "bg-blue-500/10 text-blue-500" : "bg-emerald-500/10 text-emerald-500",
              cdr.disposition === "NO ANSWER" && "bg-red-500/10 text-red-500"
            )}>
              {isInbound ? (
                <PhoneIncoming className="h-3.5 w-3.5" />
              ) : (
                <PhoneOutgoing className="h-3.5 w-3.5" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-xs font-medium">
                {displayName || displayNumber}
              </div>
              {displayName && (
                <div className="truncate text-[10px] text-muted-foreground font-mono">
                  {displayNumber}
                </div>
              )}
            </div>
            <div className="text-right shrink-0">
              <div className="text-[10px] text-muted-foreground font-mono">
                {mins > 0 ? `${mins}:${String(secs).padStart(2, "0")}` : `${secs}s`}
              </div>
              <div className="text-[9px] text-muted-foreground/60">
                {new Date(cdr.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </div>
            </div>
          </button>
        )
      })}
    </div>
  )
}

// ── Voicemail Tab ───────────────────────────────────────────────────
function VoicemailTab() {
  const { data: boxes } = useVoicemailBoxes()
  const firstBox = boxes?.[0] ?? null
  const { data: messages, isLoading } = useVoicemailMessages(firstBox?.id ?? null)
  const { makeCall, callState } = useSoftphoneStore()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
      </div>
    )
  }

  if (!messages?.length) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <Voicemail className="mb-2 h-6 w-6 opacity-40" />
        <span className="text-xs">No voicemail messages</span>
      </div>
    )
  }

  return (
    <div className="divide-y overflow-auto">
      {messages.map((msg: VoicemailMessage) => {
        const duration = msg.duration_seconds
        const mins = Math.floor(duration / 60)
        const secs = duration % 60

        return (
          <div
            key={msg.id}
            className={cn(
              "flex items-center gap-2.5 px-3 py-2.5 transition-colors hover:bg-accent/50",
              !msg.is_read && "bg-primary/5"
            )}
          >
            <div className="flex items-center justify-center h-7 w-7 rounded-full shrink-0 bg-violet-500/10 text-violet-500">
              <Voicemail className="h-3.5 w-3.5" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <span className="truncate text-xs font-medium">
                  {msg.caller_name || msg.caller_number}
                </span>
                {!msg.is_read && (
                  <div className="h-1.5 w-1.5 rounded-full bg-primary shrink-0" />
                )}
                {msg.is_urgent && (
                  <Badge variant="destructive" className="h-3.5 px-1 text-[8px]">!</Badge>
                )}
              </div>
              {msg.caller_name && (
                <div className="truncate text-[10px] text-muted-foreground font-mono">
                  {msg.caller_number}
                </div>
              )}
            </div>
            <div className="text-right shrink-0">
              <div className="text-[10px] text-muted-foreground font-mono">
                {mins > 0 ? `${mins}:${String(secs).padStart(2, "0")}` : `${secs}s`}
              </div>
              <div className="text-[9px] text-muted-foreground/60">
                {new Date(msg.created_at).toLocaleDateString([], { month: "short", day: "numeric" })}
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 shrink-0"
              onClick={() => callState === "idle" && makeCall(msg.caller_number)}
            >
              <Phone className="h-3 w-3" />
            </Button>
          </div>
        )
      })}
    </div>
  )
}

// ── Active Call Display (Center) ────────────────────────────────────
function ActiveCallDisplay() {
  const { t } = useTranslation()
  const {
    callState,
    callDirection,
    remoteIdentity,
    callStartTime,
    isMuted,
    isOnHold,
    transferMode,
    consultRemoteIdentity,
    consultCallState,
    toggleMute,
    toggleHold,
    hangup,
    answerCall,
    declineCall,
    sendDTMF,
    startTransfer,
    cancelTransfer,
    blindTransfer,
    startConsultTransfer,
    completeAttendedTransfer,
    cancelConsult,
  } = useSoftphoneStore()
  const elapsed = useCallTimer(callStartTime)
  const [showDtmf, setShowDtmf] = useState(false)
  const [transferSearch, setTransferSearch] = useState("")
  const [transferTab, setTransferTab] = useState<"blind" | "attended">("blind")
  const { data: extensions } = useExtensions()

  const isIdle = callState === "idle"
  const isRingingIn = callState === "ringing_in"

  // Extension search for transfer
  const transferTargets = useMemo(() => {
    if (!extensions || !transferSearch.trim()) return extensions ?? []
    const q = transferSearch.toLowerCase()
    return extensions.filter(
      (e) =>
        e.extension_number.includes(q) ||
        (e.internal_cid_name ?? "").toLowerCase().includes(q)
    )
  }, [extensions, transferSearch])

  if (isIdle) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-muted-foreground">
        <div className="relative mb-4">
          <div className="h-20 w-20 rounded-full bg-muted/50 flex items-center justify-center">
            <Phone className="h-8 w-8 opacity-30" />
          </div>
        </div>
        <span className="text-sm font-medium opacity-60">{t("softphone.page.noActiveCall")}</span>
        <span className="text-xs opacity-40 mt-1">{t("softphone.page.dialToStart")}</span>
      </div>
    )
  }

  if (isRingingIn) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center">
        <div className="relative mb-4">
          <div className="h-20 w-20 rounded-full bg-blue-500/10 flex items-center justify-center animate-pulse">
            <PhoneIncoming className="h-8 w-8 text-blue-500" />
          </div>
          <div className="absolute inset-0 rounded-full border-2 border-blue-500/30 animate-ping" />
        </div>
        <span className="text-lg font-semibold font-mono">{remoteIdentity}</span>
        <Badge variant="secondary" className="mt-2">{t("softphone.incomingCall")}</Badge>
        <div className="flex items-center gap-4 mt-6">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="destructive"
                size="icon"
                className="size-14 rounded-full"
                onClick={declineCall}
              >
                <PhoneOff className="size-6" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>{t("softphone.reject")}</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="icon"
                className="size-14 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white"
                onClick={answerCall}
              >
                <Phone className="size-6" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>{t("softphone.accept")}</TooltipContent>
          </Tooltip>
        </div>
      </div>
    )
  }

  // Active call (connected, on_hold, ringing_out)
  return (
    <div className="flex flex-1 flex-col items-center justify-center">
      {/* Caller display */}
      <div className="relative mb-3">
        <div className={cn(
          "h-20 w-20 rounded-full flex items-center justify-center text-2xl font-bold",
          callState === "on_hold" ? "bg-amber-500/10 text-amber-500" : "bg-emerald-500/10 text-emerald-500"
        )}>
          {remoteIdentity?.charAt(0)?.toUpperCase() || "?"}
        </div>
        {callState === "ringing_out" && (
          <div className="absolute inset-0 rounded-full border-2 border-emerald-500/30 animate-ping" />
        )}
      </div>
      <span className="text-lg font-semibold font-mono">{remoteIdentity}</span>
      <div className="flex items-center gap-2 mt-1">
        {callState === "ringing_out" && (
          <Badge variant="secondary">{t("softphone.ringing")}</Badge>
        )}
        {callState === "on_hold" && (
          <Badge variant="outline" className="border-amber-500 text-amber-600">{t("softphone.onHold")}</Badge>
        )}
        {callState === "connected" && elapsed && (
          <span className="text-sm text-muted-foreground font-mono">{elapsed}</span>
        )}
        {callDirection && (
          <span className="text-[10px] text-muted-foreground/60 uppercase">{callDirection}</span>
        )}
      </div>

      {/* Consult call info */}
      {(transferMode === "consulting" || transferMode === "attended") && (
        <div className="mt-3 px-4 py-2 rounded-lg bg-blue-500/5 border border-blue-500/20 text-center">
          <span className="text-[10px] text-blue-500 uppercase font-medium">
            {consultCallState === "ringing" ? "Consulting..." : "Consult Connected"}
          </span>
          <div className="text-sm font-mono font-medium mt-0.5">{consultRemoteIdentity}</div>
        </div>
      )}

      {/* Call controls */}
      <div className="flex items-center gap-2 mt-6">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant={isMuted ? "destructive" : "outline"}
              size="icon"
              className="size-11 rounded-full"
              onClick={toggleMute}
            >
              {isMuted ? <MicOff className="size-4" /> : <Mic className="size-4" />}
            </Button>
          </TooltipTrigger>
          <TooltipContent>{isMuted ? t("softphone.unmute") : t("softphone.mute")}</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant={isOnHold ? "default" : "outline"}
              size="icon"
              className="size-11 rounded-full"
              onClick={toggleHold}
            >
              {isOnHold ? <Play className="size-4" /> : <Pause className="size-4" />}
            </Button>
          </TooltipTrigger>
          <TooltipContent>{isOnHold ? t("softphone.unhold") : t("softphone.hold")}</TooltipContent>
        </Tooltip>

        {callState !== "ringing_out" && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant={transferMode !== "idle" ? "default" : "outline"}
                size="icon"
                className="size-11 rounded-full"
                onClick={() => transferMode === "idle" ? startTransfer() : cancelTransfer()}
              >
                <ArrowRightLeft className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>{t("softphone.transfer")}</TooltipContent>
          </Tooltip>
        )}

        {callState === "connected" && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                className="size-11 rounded-full"
                onClick={() => sendDTMF("*85")}
              >
                <ParkingSquare className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>{t("softphone.park")}</TooltipContent>
          </Tooltip>
        )}

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              className={cn("size-11 rounded-full", showDtmf && "bg-accent")}
              onClick={() => setShowDtmf(!showDtmf)}
            >
              <Hash className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t("softphone.dtmf")}</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="destructive"
              size="icon"
              className="size-12 rounded-full"
              onClick={hangup}
            >
              <PhoneOff className="size-5" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t("softphone.hangUp")}</TooltipContent>
        </Tooltip>
      </div>

      {/* Attended transfer controls */}
      {transferMode === "attended" && consultCallState === "connected" && (
        <div className="flex items-center gap-2 mt-3">
          <Button
            size="sm"
            className="bg-emerald-600 hover:bg-emerald-700 text-white"
            onClick={completeAttendedTransfer}
          >
            <Check className="size-3.5 mr-1" />
            Complete Transfer
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={cancelConsult}
          >
            <X className="size-3.5 mr-1" />
            Cancel
          </Button>
        </div>
      )}

      {/* DTMF pad */}
      {showDtmf && (
        <div className="grid grid-cols-3 gap-1 mt-4 w-48">
          {KEYS.flat().map((key) => (
            <Button
              key={key}
              variant="outline"
              size="sm"
              className="h-9 font-mono"
              onClick={() => sendDTMF(key)}
            >
              {key}
            </Button>
          ))}
        </div>
      )}

      {/* Transfer panel */}
      {transferMode === "selecting" && (
        <div className="mt-4 w-full max-w-xs border rounded-lg bg-card p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Transfer</span>
            <Button variant="ghost" size="icon" className="h-5 w-5" onClick={cancelTransfer}>
              <X className="h-3 w-3" />
            </Button>
          </div>
          <Tabs value={transferTab} onValueChange={(v) => setTransferTab(v as "blind" | "attended")}>
            <TabsList className="w-full h-7">
              <TabsTrigger value="blind" className="text-[11px] h-5 flex-1">Blind</TabsTrigger>
              <TabsTrigger value="attended" className="text-[11px] h-5 flex-1">Attended</TabsTrigger>
            </TabsList>
          </Tabs>
          <div className="relative mt-2">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
            <Input
              value={transferSearch}
              onChange={(e) => setTransferSearch(e.target.value)}
              placeholder="Search extension..."
              className="h-7 pl-7 text-xs"
              autoFocus
            />
          </div>
          <div className="mt-2 max-h-32 overflow-auto divide-y">
            {transferTargets.slice(0, 10).map((ext) => (
              <button
                key={ext.id}
                className="flex items-center gap-2 w-full px-2 py-1.5 text-left hover:bg-accent/50 transition-colors"
                onClick={() => {
                  if (transferTab === "blind") {
                    blindTransfer(ext.extension_number)
                  } else {
                    startConsultTransfer(ext.extension_number)
                  }
                }}
              >
                <div className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  STATUS_CONFIG[getExtensionStatus(ext)].dot
                )} />
                <span className="font-mono text-[11px] font-medium">{ext.extension_number}</span>
                <span className="text-[10px] text-muted-foreground truncate">
                  {ext.internal_cid_name}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Extension Directory (Right Panel) ───────────────────────────────
function ExtensionDirectory({
  onExtensionClick,
}: {
  onExtensionClick?: (extNumber: string) => void
}) {
  const [search, setSearch] = useState("")
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null)
  const role = useAuthStore((s) => s.user?.role)
  const isMsp = role ? isMspRole(role) : false
  const { data: tenants } = useTenants()
  const { data: extensions, isLoading } = useTenantExtensions(selectedTenantId)

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

  const sortedExtensions = useMemo(() => {
    const order: Record<ExtStatus, number> = { ringing: 0, busy: 1, available: 2, dnd: 3, offline: 4 }
    return [...filteredExtensions].sort((a, b) => {
      const sa = getExtensionStatus(a)
      const sb = getExtensionStatus(b)
      if (order[sa] !== order[sb]) return order[sa] - order[sb]
      return a.extension_number.localeCompare(b.extension_number, undefined, { numeric: true })
    })
  }, [filteredExtensions])

  return (
    <div className="flex flex-col rounded-lg border bg-card">
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <Users className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Extensions
        </span>
        <Badge variant="secondary" className="ml-auto h-4 min-w-[18px] px-1 text-[10px] font-mono">
          {filteredExtensions.length}
        </Badge>
      </div>
      <div className="p-2 space-y-2">
        {isMsp && tenants && tenants.length > 1 && (
          <Select
            value={selectedTenantId ?? "__current__"}
            onValueChange={(v) => setSelectedTenantId(v === "__current__" ? null : v)}
          >
            <SelectTrigger className="h-7 text-xs">
              <Building2 className="h-3 w-3 mr-1 text-muted-foreground" />
              <SelectValue placeholder="All tenants" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__current__">Current tenant</SelectItem>
              {tenants.map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  {t.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search..."
            className="h-7 pl-7 text-xs"
          />
        </div>
      </div>
      <div className="flex-1 overflow-auto p-2 pt-0 max-h-[300px]">
        {isLoading ? (
          <div className="flex items-center justify-center py-6">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
          </div>
        ) : sortedExtensions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-6 text-muted-foreground">
            <Phone className="mb-1 h-4 w-4 opacity-40" />
            <span className="text-[10px]">No extensions found</span>
          </div>
        ) : (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(68px,1fr))] gap-1">
            {sortedExtensions.map((ext) => (
              <ExtensionTile
                key={ext.id}
                extensionNumber={ext.extension_number}
                name={ext.internal_cid_name ?? ""}
                status={getExtensionStatus(ext)}
                onClick={() => onExtensionClick?.(ext.extension_number)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Queue Stats (Right Panel) ───────────────────────────────────────
function QueueStatsPanel() {
  const { data: stats } = useQueueStats()

  if (!stats?.length) {
    return (
      <div className="flex flex-col rounded-lg border bg-card">
        <div className="flex items-center gap-2 border-b px-3 py-2">
          <Headset className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Queues</span>
        </div>
        <div className="flex flex-col items-center justify-center py-4 text-muted-foreground">
          <Headset className="mb-1 h-4 w-4 opacity-40" />
          <span className="text-[10px]">No queues</span>
        </div>
      </div>
    )
  }

  const totalWaiting = stats.reduce((a, q) => a + q.waiting_count, 0)

  return (
    <div className="flex flex-col rounded-lg border bg-card">
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <Headset className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Queues</span>
        {totalWaiting > 0 && (
          <Badge variant="destructive" className="ml-auto h-4 min-w-[18px] px-1 text-[10px] font-mono">
            {totalWaiting}
          </Badge>
        )}
      </div>
      <div className="divide-y">
        {stats.map((q) => (
          <div key={q.queue_id} className="px-3 py-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium truncate">{q.queue_name}</span>
              {q.waiting_count > 0 && (
                <Badge variant="destructive" className="h-4 px-1 text-[10px] font-mono">
                  {q.waiting_count}
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
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main Softphone Page ─────────────────────────────────────────────
export function SoftphonePage() {
  const { t } = useTranslation()
  const remoteAudioRef = useRef<HTMLAudioElement>(null)
  const { status } = useSoftphoneInit(remoteAudioRef)
  useHeadset()
  const {
    callState,
    transferMode,
    makeCall,
    blindTransfer,
    startTransfer,
  } = useSoftphoneStore()

  const isInCall = callState !== "idle"

  // Click extension → if in transfer mode, transfer; otherwise call
  const handleExtensionClick = useCallback((extNumber: string) => {
    if (transferMode === "selecting") {
      blindTransfer(extNumber)
    } else if (isInCall) {
      startTransfer()
      // After a tick, the UI will show the transfer panel
      setTimeout(() => {
        useSoftphoneStore.getState().blindTransfer(extNumber)
      }, 0)
    } else {
      makeCall(extNumber)
    }
  }, [transferMode, isInCall, blindTransfer, startTransfer, makeCall])

  // Pickup parked call
  const handlePickup = useCallback((slotNumber: number) => {
    if (callState === "idle") {
      makeCall(`*86${slotNumber}`)
    }
  }, [callState, makeCall])

  return (
    <>
      <audio ref={remoteAudioRef} autoPlay />
      <div className="flex h-[calc(100vh-3.5rem)] flex-col overflow-hidden">
        {/* ── Top Bar ─────────────────────────────────────────── */}
        <div className="flex items-center gap-3 border-b bg-card px-4 py-2">
          <div className="flex items-center gap-2">
            <Phone className="h-4 w-4 text-emerald-500" />
            <span className="text-sm font-semibold tracking-tight">{t("softphone.title")}</span>
          </div>

          <div className="mx-3 h-4 w-px bg-border" />

          {/* Registration status */}
          <div className="flex items-center gap-1.5">
            <div className={cn(
              "h-2 w-2 rounded-full",
              status === "registered" && "bg-emerald-400",
              status === "connecting" && "bg-amber-400 animate-pulse",
              status === "disconnected" && "bg-zinc-400",
              status === "error" && "bg-red-400",
            )} />
            <span className="text-[10px] text-muted-foreground capitalize">{status}</span>
          </div>

          <div className="flex-1" />
          <LiveClock />
        </div>

        {/* ── Main Content ────────────────────────────────────── */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left Panel — Dialpad / Recent / Voicemail */}
          <div className="flex w-[300px] shrink-0 flex-col border-r bg-muted/20">
            <Tabs defaultValue="dialpad" className="flex flex-1 flex-col">
              <TabsList className="mx-2 mt-2 h-8 w-auto">
                <TabsTrigger value="dialpad" className="text-[11px] h-6 gap-1 px-2.5">
                  <Hash className="h-3 w-3" />
                  {t("softphone.dial")}
                </TabsTrigger>
                <TabsTrigger value="recent" className="text-[11px] h-6 gap-1 px-2.5">
                  <History className="h-3 w-3" />
                  {t("softphone.page.recent")}
                </TabsTrigger>
                <TabsTrigger value="voicemail" className="text-[11px] h-6 gap-1 px-2.5">
                  <Voicemail className="h-3 w-3" />
                  {t("softphone.page.voicemail")}
                </TabsTrigger>
              </TabsList>
              <TabsContent value="dialpad" className="flex-1 mt-0">
                <DialpadTab />
              </TabsContent>
              <TabsContent value="recent" className="flex-1 mt-0 overflow-auto">
                <RecentTab />
              </TabsContent>
              <TabsContent value="voicemail" className="flex-1 mt-0 overflow-auto">
                <VoicemailTab />
              </TabsContent>
            </Tabs>
          </div>

          {/* Center Panel — Active Call */}
          <div className="flex flex-1 flex-col overflow-hidden bg-background">
            <ActiveCallDisplay />
          </div>

          {/* Right Panel — Extensions / Parking / Queues */}
          <div className="flex w-[320px] shrink-0 flex-col gap-2 overflow-auto border-l bg-muted/20 p-2">
            <ExtensionDirectory onExtensionClick={handleExtensionClick} />
            <ParkingPanel onPickup={handlePickup} />
            <QueueStatsPanel />
          </div>
        </div>
      </div>
    </>
  )
}
