import { useState, useEffect, useMemo, useCallback, useRef } from "react"
import { useTranslation } from "react-i18next"
import {
  Phone,
  PhoneOff,
  PhoneIncoming,
  PhoneOutgoing,
  PhoneMissed,
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
  RotateCcw,
  ArrowRightLeft,
  X,
  Check,
  Building2,
  Loader2,
  Delete,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
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
    <span className="font-mono text-xs tabular-nums text-muted-foreground/70">
      {now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
    </span>
  )
}

// ── Dial pad keys ───────────────────────────────────────────────────
const DIAL_KEYS: Array<{ digit: string; letters: string }> = [
  { digit: "1", letters: "" },
  { digit: "2", letters: "ABC" },
  { digit: "3", letters: "DEF" },
  { digit: "4", letters: "GHI" },
  { digit: "5", letters: "JKL" },
  { digit: "6", letters: "MNO" },
  { digit: "7", letters: "PQRS" },
  { digit: "8", letters: "TUV" },
  { digit: "9", letters: "WXYZ" },
  { digit: "*", letters: "" },
  { digit: "0", letters: "+" },
  { digit: "#", letters: "" },
]

const KEYS = [
  ["1", "2", "3"],
  ["4", "5", "6"],
  ["7", "8", "9"],
  ["*", "0", "#"],
]

// ── Section Card wrapper ────────────────────────────────────────────
function SectionCard({
  icon: Icon,
  title,
  badge,
  accent = "indigo",
  children,
  className,
}: {
  icon: React.ComponentType<{ className?: string }>
  title: string
  badge?: React.ReactNode
  accent?: "indigo" | "teal" | "amber" | "violet" | "green"
  children: React.ReactNode
  className?: string
}) {
  const accentStyles = {
    indigo: {
      border: "border-[oklch(0.50_0.20_265_/_20%)]",
      headerBg: "bg-gradient-to-r from-[oklch(0.50_0.20_265_/_12%)] to-transparent",
      icon: "text-[oklch(0.65_0.22_265)]",
      topLine: "from-[oklch(0.55_0.22_265)] to-[oklch(0.65_0.20_285)]",
    },
    teal: {
      border: "border-[oklch(0.55_0.14_185_/_20%)]",
      headerBg: "bg-gradient-to-r from-[oklch(0.55_0.14_185_/_12%)] to-transparent",
      icon: "text-[oklch(0.68_0.16_185)]",
      topLine: "from-[oklch(0.62_0.16_185)] to-[oklch(0.58_0.14_170)]",
    },
    amber: {
      border: "border-[oklch(0.65_0.16_75_/_20%)]",
      headerBg: "bg-gradient-to-r from-[oklch(0.65_0.16_75_/_12%)] to-transparent",
      icon: "text-[oklch(0.75_0.16_75)]",
      topLine: "from-[oklch(0.72_0.16_75)] to-[oklch(0.68_0.14_55)]",
    },
    violet: {
      border: "border-[oklch(0.50_0.18_300_/_20%)]",
      headerBg: "bg-gradient-to-r from-[oklch(0.50_0.18_300_/_12%)] to-transparent",
      icon: "text-[oklch(0.68_0.20_300)]",
      topLine: "from-[oklch(0.60_0.20_300)] to-[oklch(0.55_0.18_320)]",
    },
    green: {
      border: "border-[oklch(0.50_0.17_155_/_20%)]",
      headerBg: "bg-gradient-to-r from-[oklch(0.50_0.17_155_/_12%)] to-transparent",
      icon: "text-[oklch(0.65_0.19_155)]",
      topLine: "from-[oklch(0.60_0.19_155)] to-[oklch(0.55_0.17_170)]",
    },
  }
  const a = accentStyles[accent]

  return (
    <div className={cn(
      "flex flex-col rounded-2xl border bg-card/80 backdrop-blur-sm overflow-hidden",
      "shadow-[0_2px_12px_oklch(0_0_0_/_10%)]",
      a.border,
      className,
    )}>
      {/* Colored top accent line */}
      <div className={cn("h-[2px] bg-gradient-to-r", a.topLine)} />
      <div className={cn("flex items-center gap-2.5 border-b border-border/30 px-4 py-2.5", a.headerBg)}>
        <Icon className={cn("h-4 w-4", a.icon)} />
        <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          {title}
        </span>
        {badge && <div className="ml-auto">{badge}</div>}
      </div>
      {children}
    </div>
  )
}

// ── Center Dial Pad (large, beautiful) ──────────────────────────────
function CenterDialpad() {
  const { t } = useTranslation()
  const [number, setNumber] = useState("")
  const { callState, makeCall, sendDTMF, lastDialedNumber } = useSoftphoneStore()
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
    <div className="flex flex-col items-center w-full max-w-sm mx-auto">
      {/* Number display */}
      <div className="relative w-full mb-5">
        <input
          value={number}
          onChange={(e) => setNumber(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t("softphone.enterNumber")}
          className={cn(
            "w-full text-center text-2xl font-bold tracking-[0.08em] h-14 rounded-2xl",
            "bg-[var(--sp-surface)] border border-border/60",
            "text-foreground",
            "placeholder:text-muted-foreground/30 placeholder:text-lg placeholder:font-normal placeholder:tracking-normal",
            "focus:outline-none focus:border-primary/50",
            "focus:shadow-[0_0_0_3px_var(--sp-glow),0_0_20px_var(--sp-glow)]",
            "transition-all duration-200",
          )}
        />
        {number && (
          <button
            onClick={() => setNumber((prev) => prev.slice(0, -1))}
            className="absolute right-4 top-1/2 -translate-y-1/2 p-1 rounded-lg text-muted-foreground/50 hover:text-foreground hover:bg-accent transition-all"
          >
            <Delete className="size-5" />
          </button>
        )}
      </div>

      {/* Dial pad grid */}
      <div className="grid grid-cols-3 gap-3 w-full">
        {DIAL_KEYS.map(({ digit, letters }) => (
          <button
            key={digit}
            onClick={() => handleKey(digit)}
            className={cn(
              "sp-dial-btn group relative flex flex-col items-center justify-center",
              "h-[4.5rem] rounded-2xl",
              "bg-[var(--sp-surface)] border border-border/60",
              "shadow-[0_1px_3px_oklch(0_0_0_/_10%),inset_0_1px_0_oklch(1_0_0_/_5%)]",
              "hover:bg-accent hover:border-primary/30 hover:-translate-y-[1px]",
              "hover:shadow-[0_4px_20px_oklch(0.55_0.22_265_/_20%),inset_0_1px_0_oklch(1_0_0_/_6%)]",
              "active:translate-y-0 active:shadow-[inset_0_2px_4px_oklch(0_0_0_/_15%)]",
              "transition-all duration-150",
            )}
          >
            <span className="text-2xl font-semibold leading-none">{digit}</span>
            {letters && (
              <span className="text-[9px] font-semibold tracking-[0.2em] text-muted-foreground/50 mt-1 leading-none">
                {letters}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Call button */}
      {!inCall && (
        <button
          onClick={handleCall}
          disabled={!number.trim() || callState !== "idle"}
          className={cn(
            "flex items-center justify-center gap-2.5 w-full h-14 rounded-2xl font-bold text-base mt-4",
            "bg-gradient-to-r from-[var(--sp-call-green)] to-[oklch(0.52_0.20_160)]",
            "text-white",
            "shadow-[0_4px_20px_oklch(from_var(--sp-call-green)_l_c_h_/_35%),0_1px_4px_oklch(from_var(--sp-call-green)_l_c_h_/_25%)]",
            "hover:shadow-[0_6px_28px_oklch(from_var(--sp-call-green)_l_c_h_/_50%),0_2px_8px_oklch(from_var(--sp-call-green)_l_c_h_/_30%)]",
            "hover:brightness-105 hover:-translate-y-[1px]",
            "active:translate-y-0 active:brightness-95 active:shadow-[0_2px_8px_oklch(0.62_0.19_155_/_20%)]",
            "disabled:opacity-30 disabled:shadow-none disabled:pointer-events-none disabled:translate-y-0",
            "transition-all duration-200",
          )}
        >
          <Phone className="size-5" />
          {t("softphone.call")}
        </button>
      )}

      {/* Redial */}
      {!inCall && lastDialedNumber && !number.trim() && callState === "idle" && (
        <button
          onClick={() => makeCall(lastDialedNumber)}
          className="flex items-center justify-center gap-2 w-full h-11 rounded-2xl text-sm font-medium text-muted-foreground hover:text-foreground border border-border/40 hover:border-border/60 hover:bg-accent/50 mt-3 transition-all"
        >
          <RotateCcw className="size-3.5" />
          {t("softphone.redial", { number: lastDialedNumber })}
        </button>
      )}
    </div>
  )
}

// ── Recent Calls List ───────────────────────────────────────────────
function RecentCallsList() {
  const { data: cdrs, isLoading } = useCdrs({ limit: 30 })
  const { makeCall, callState } = useSoftphoneStore()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
      </div>
    )
  }

  if (!cdrs?.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <div className="size-14 rounded-2xl bg-[oklch(0.55_0.22_265_/_8%)] flex items-center justify-center mb-3">
          <History className="h-6 w-6 text-[oklch(0.55_0.18_265_/_40%)]" />
        </div>
        <span className="text-sm font-medium opacity-50">No recent calls</span>
      </div>
    )
  }

  return (
    <div className="divide-y divide-border/30 overflow-auto">
      {cdrs.map((cdr: CDR) => {
        const isInbound = cdr.direction === "inbound"
        const displayNumber = isInbound ? cdr.caller_number : cdr.called_number
        const displayName = isInbound ? cdr.caller_name : ""
        const duration = cdr.duration_seconds
        const mins = Math.floor(duration / 60)
        const secs = duration % 60
        const missed = cdr.disposition === "NO ANSWER"

        return (
          <button
            key={cdr.id}
            className="group flex items-center gap-3 px-4 py-3 w-full text-left hover:bg-accent/40 transition-all duration-150"
            onClick={() => callState === "idle" && makeCall(displayNumber)}
          >
            <div className={cn(
              "flex items-center justify-center size-10 rounded-xl shrink-0 transition-colors",
              missed
                ? "bg-[oklch(0.58_0.22_25_/_8%)] text-[var(--sp-call-red)]"
                : isInbound
                  ? "bg-primary/8 text-primary"
                  : "bg-[oklch(0.62_0.19_155_/_8%)] text-[var(--sp-call-green)]",
            )}>
              {missed ? (
                <PhoneMissed className="h-4 w-4" />
              ) : isInbound ? (
                <PhoneIncoming className="h-4 w-4" />
              ) : (
                <PhoneOutgoing className="h-4 w-4" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-semibold group-hover:text-primary transition-colors">
                {displayName || displayNumber}
              </div>
              {displayName && (
                <div className="truncate text-[11px] text-muted-foreground/60 font-mono">
                  {displayNumber}
                </div>
              )}
            </div>
            <div className="text-right shrink-0">
              <div className="text-[11px] text-muted-foreground/70 font-mono tabular-nums">
                {mins > 0 ? `${mins}:${String(secs).padStart(2, "0")}` : `${secs}s`}
              </div>
              <div className="text-[10px] text-muted-foreground/40">
                {new Date(cdr.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </div>
            </div>
          </button>
        )
      })}
    </div>
  )
}

// ── Voicemail List ──────────────────────────────────────────────────
function VoicemailList() {
  const { data: boxes } = useVoicemailBoxes()
  const firstBox = boxes?.[0] ?? null
  const { data: messages, isLoading } = useVoicemailMessages(firstBox?.id ?? null)
  const { makeCall, callState } = useSoftphoneStore()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
      </div>
    )
  }

  if (!messages?.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <div className="size-14 rounded-2xl bg-[oklch(0.55_0.18_300_/_8%)] flex items-center justify-center mb-3">
          <Voicemail className="h-6 w-6 text-[oklch(0.60_0.18_300_/_40%)]" />
        </div>
        <span className="text-sm font-medium opacity-50">No voicemail messages</span>
      </div>
    )
  }

  return (
    <div className="divide-y divide-border/30 overflow-auto">
      {messages.map((msg: VoicemailMessage) => {
        const duration = msg.duration_seconds
        const mins = Math.floor(duration / 60)
        const secs = duration % 60

        return (
          <div
            key={msg.id}
            className={cn(
              "flex items-center gap-3 px-4 py-3 transition-all duration-150 hover:bg-accent/40",
              !msg.is_read && "bg-primary/[3%]"
            )}
          >
            <div className="flex items-center justify-center size-10 rounded-xl shrink-0 bg-[oklch(0.60_0.18_300_/_8%)] text-[oklch(0.60_0.18_300)]">
              <Voicemail className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-semibold">
                  {msg.caller_name || msg.caller_number}
                </span>
                {!msg.is_read && (
                  <span className="size-2 rounded-full bg-primary shrink-0" />
                )}
                {msg.is_urgent && (
                  <Badge variant="destructive" className="h-4 px-1.5 text-[9px] font-bold">!</Badge>
                )}
              </div>
              {msg.caller_name && (
                <div className="truncate text-[11px] text-muted-foreground/60 font-mono">
                  {msg.caller_number}
                </div>
              )}
            </div>
            <div className="text-right shrink-0">
              <div className="text-[11px] text-muted-foreground/70 font-mono tabular-nums">
                {mins > 0 ? `${mins}:${String(secs).padStart(2, "0")}` : `${secs}s`}
              </div>
              <div className="text-[10px] text-muted-foreground/40">
                {new Date(msg.created_at).toLocaleDateString([], { month: "short", day: "numeric" })}
              </div>
            </div>
            <button
              className="flex items-center justify-center size-9 rounded-xl shrink-0 text-muted-foreground/50 hover:text-[var(--sp-call-green)] hover:bg-[oklch(0.62_0.19_155_/_8%)] transition-all"
              onClick={() => callState === "idle" && makeCall(msg.caller_number)}
            >
              <Phone className="h-3.5 w-3.5" />
            </button>
          </div>
        )
      })}
    </div>
  )
}

// ── Control Button ──────────────────────────────────────────────────
function ControlBtn({
  onClick,
  active,
  destructive,
  tooltip,
  large,
  children,
}: {
  onClick: () => void
  active?: boolean
  destructive?: boolean
  tooltip: string
  large?: boolean
  children: React.ReactNode
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          onClick={onClick}
          className={cn(
            "flex items-center justify-center rounded-2xl transition-all duration-200",
            "active:scale-90",
            large ? "size-16" : "size-14",
            destructive
              ? "bg-gradient-to-br from-[var(--sp-call-red)] to-[oklch(0.48_0.22_28)] text-white shadow-[0_4px_16px_oklch(0.58_0.22_25_/_25%)] hover:shadow-[0_6px_24px_oklch(0.58_0.22_25_/_35%)] hover:brightness-110"
              : active
                ? "bg-primary text-primary-foreground shadow-[0_4px_16px_var(--sp-glow)] hover:brightness-110"
                : "bg-[var(--sp-surface)] text-foreground border border-border/40 shadow-sm hover:bg-accent hover:border-border/60 hover:shadow-md",
          )}
        >
          {children}
        </button>
      </TooltipTrigger>
      <TooltipContent className="font-medium text-xs">{tooltip}</TooltipContent>
    </Tooltip>
  )
}

// ── Active Call Display (replaces dialpad when in call) ─────────────
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
    isAnswering,
  } = useSoftphoneStore()
  const elapsed = useCallTimer(callStartTime)
  const [showDtmf, setShowDtmf] = useState(false)
  const [transferSearch, setTransferSearch] = useState("")
  const [transferTab, setTransferTab] = useState<"blind" | "attended">("blind")
  const { data: extensions } = useExtensions()

  const isRingingIn = callState === "ringing_in"

  const transferTargets = useMemo(() => {
    if (!extensions || !transferSearch.trim()) return extensions ?? []
    const q = transferSearch.toLowerCase()
    return extensions.filter(
      (e) =>
        e.extension_number.includes(q) ||
        (e.internal_cid_name ?? "").toLowerCase().includes(q)
    )
  }, [extensions, transferSearch])

  // Incoming call
  if (isRingingIn) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 sp-animate-in">
        {/* Ripple rings */}
        <div className="relative mb-8">
          <span className="absolute inset-[-20px] rounded-full border-2 border-[var(--sp-call-green)]/40 animate-[sp-ripple_2s_ease-out_infinite]" />
          <span className="absolute inset-[-20px] rounded-full border-2 border-[var(--sp-call-green)]/40 animate-[sp-ripple_2s_ease-out_0.6s_infinite]" />
          <span className="absolute inset-[-20px] rounded-full border-2 border-[var(--sp-call-green)]/40 animate-[sp-ripple_2s_ease-out_1.2s_infinite]" />
          <div className={cn(
            "relative flex items-center justify-center size-28 rounded-full",
            "bg-gradient-to-br from-[oklch(0.62_0.19_155)] to-[oklch(0.48_0.17_165)]",
            "shadow-[0_8px_40px_oklch(0.62_0.19_155_/_35%)]",
            "animate-[sp-incoming-glow_2s_ease-in-out_infinite]",
          )}>
            <PhoneIncoming className="size-12 text-white" />
          </div>
        </div>

        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest bg-[oklch(0.62_0.19_155_/_12%)] text-[var(--sp-call-green)] mb-3">
          <span className="size-1.5 rounded-full bg-[var(--sp-call-green)] animate-pulse" />
          {t("softphone.incomingCall")}
        </span>

        <span className="text-3xl font-bold tracking-tight">{remoteIdentity}</span>

        <div className="flex items-center gap-8 mt-10">
          <div className="flex flex-col items-center gap-2.5">
            <button
              onClick={declineCall}
              className={cn(
                "flex items-center justify-center size-18 rounded-full",
                "bg-gradient-to-br from-[var(--sp-call-red)] to-[oklch(0.48_0.22_28)]",
                "text-white shadow-[0_6px_24px_oklch(0.58_0.22_25_/_30%)]",
                "hover:shadow-[0_8px_32px_oklch(0.58_0.22_25_/_40%)] hover:brightness-110",
                "active:scale-90 transition-all duration-200",
              )}
            >
              <PhoneOff className="size-7" />
            </button>
            <span className="text-xs font-semibold text-muted-foreground">{t("softphone.reject")}</span>
          </div>
          <div className="flex flex-col items-center gap-2.5">
            <button
              onClick={answerCall}
              disabled={isAnswering}
              className={cn(
                "flex items-center justify-center size-18 rounded-full",
                "bg-gradient-to-br from-[var(--sp-call-green)] to-[oklch(0.48_0.17_165)]",
                "text-white shadow-[0_6px_24px_oklch(0.62_0.19_155_/_30%)]",
                "hover:shadow-[0_8px_32px_oklch(0.62_0.19_155_/_40%)] hover:brightness-110",
                "active:scale-90 transition-all duration-200",
                "disabled:opacity-60",
              )}
            >
              {isAnswering ? (
                <Loader2 className="size-7 animate-spin" />
              ) : (
                <Phone className="size-7" />
              )}
            </button>
            <span className="text-xs font-semibold text-muted-foreground">{t("softphone.accept")}</span>
          </div>
        </div>
      </div>
    )
  }

  // Active / ringing out / on hold
  const initial = remoteIdentity?.charAt(0)?.toUpperCase() || "?"

  return (
    <div className="flex flex-col items-center justify-center flex-1 sp-animate-in">
      {/* Avatar */}
      <div className="relative mb-5">
        <div className={cn(
          "flex items-center justify-center size-28 rounded-full text-4xl font-bold transition-all duration-500",
          callState === "on_hold"
            ? "bg-gradient-to-br from-[var(--sp-hold-amber)] to-[oklch(0.60_0.16_80)] text-white shadow-[0_8px_32px_oklch(0.72_0.16_75_/_30%)]"
            : "bg-gradient-to-br from-[oklch(0.50_0.20_265)] to-[oklch(0.38_0.18_275)] text-white shadow-[0_8px_32px_oklch(0.42_0.18_265_/_30%)]",
        )}>
          {initial}
        </div>
        {callState === "ringing_out" && (
          <span className="absolute inset-0 rounded-full border-2 border-primary/30 animate-ping" />
        )}
      </div>

      <span className="text-3xl font-bold tracking-tight">{remoteIdentity}</span>

      <div className="flex items-center gap-2.5 mt-3">
        {callState === "ringing_out" && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-primary/10 text-primary">
            <span className="size-1.5 rounded-full bg-primary animate-pulse" />
            {t("softphone.ringing")}
          </span>
        )}
        {callState === "on_hold" && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-[oklch(0.72_0.16_75_/_15%)] text-[var(--sp-hold-amber)]">
            <span className="size-1.5 rounded-full bg-[var(--sp-hold-amber)]" />
            {t("softphone.onHold")}
          </span>
        )}
        {callState === "connected" && elapsed && (
          <span className="text-xl font-mono text-muted-foreground/70 tabular-nums tracking-wider">{elapsed}</span>
        )}
        {callDirection && (
          <span className="text-[10px] text-muted-foreground/40 uppercase font-semibold tracking-wider">{callDirection}</span>
        )}
      </div>

      {/* Consult call info */}
      {(transferMode === "consulting" || transferMode === "attended") && (
        <div className="mt-5 px-6 py-3 rounded-2xl bg-primary/5 border border-primary/15 text-center">
          <span className="text-[10px] text-primary uppercase font-bold tracking-wider">
            {consultCallState === "ringing" ? "Consulting..." : "Consult Connected"}
          </span>
          <div className="text-sm font-bold mt-1">{consultRemoteIdentity}</div>
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center gap-3 mt-10">
        <ControlBtn onClick={toggleMute} active={isMuted} tooltip={isMuted ? t("softphone.unmute") : t("softphone.mute")}>
          {isMuted ? <MicOff className="size-6" /> : <Mic className="size-6" />}
        </ControlBtn>

        <ControlBtn onClick={toggleHold} active={isOnHold} tooltip={isOnHold ? t("softphone.unhold") : t("softphone.hold")}>
          {isOnHold ? <Play className="size-6" /> : <Pause className="size-6" />}
        </ControlBtn>

        {callState !== "ringing_out" && (
          <ControlBtn
            onClick={() => transferMode === "idle" ? startTransfer() : cancelTransfer()}
            active={transferMode !== "idle"}
            tooltip={t("softphone.transfer")}
          >
            <ArrowRightLeft className="size-6" />
          </ControlBtn>
        )}

        {callState === "connected" && (
          <ControlBtn onClick={() => sendDTMF("*85")} tooltip={t("softphone.park")}>
            <ParkingSquare className="size-6" />
          </ControlBtn>
        )}

        <ControlBtn onClick={() => setShowDtmf(!showDtmf)} active={showDtmf} tooltip={t("softphone.dtmf")}>
          <Hash className="size-6" />
        </ControlBtn>

        <ControlBtn onClick={hangup} destructive large tooltip={t("softphone.hangUp")}>
          <PhoneOff className="size-7" />
        </ControlBtn>
      </div>

      {/* Attended transfer controls */}
      {transferMode === "attended" && consultCallState === "connected" && (
        <div className="flex items-center gap-3 mt-5">
          <button
            onClick={completeAttendedTransfer}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold bg-gradient-to-r from-[var(--sp-call-green)] to-[oklch(0.55_0.19_160)] text-white shadow-md hover:brightness-105 active:scale-95 transition-all"
          >
            <Check className="size-4" />
            Complete Transfer
          </button>
          <button
            onClick={cancelConsult}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium border border-border/50 hover:bg-accent transition-all"
          >
            <X className="size-4" />
            Cancel
          </button>
        </div>
      )}

      {/* DTMF pad */}
      {showDtmf && (
        <div className="grid grid-cols-3 gap-2 mt-6 w-56">
          {KEYS.flat().map((key) => (
            <button
              key={key}
              onClick={() => sendDTMF(key)}
              className="sp-dial-btn h-12 rounded-xl bg-[var(--sp-surface)] hover:bg-accent border border-border/40 hover:border-border/60 font-mono text-lg font-bold shadow-sm transition-all"
            >
              {key}
            </button>
          ))}
        </div>
      )}

      {/* Transfer panel */}
      {transferMode === "selecting" && (
        <div className="mt-6 w-full max-w-xs rounded-2xl border border-border/50 bg-card/90 backdrop-blur-sm shadow-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Transfer</span>
            <button className="size-7 flex items-center justify-center rounded-lg hover:bg-accent transition-colors" onClick={cancelTransfer}>
              <X className="h-4 w-4" />
            </button>
          </div>
          <Tabs value={transferTab} onValueChange={(v) => setTransferTab(v as "blind" | "attended")}>
            <TabsList className="w-full h-9">
              <TabsTrigger value="blind" className="text-xs h-7 flex-1">Blind</TabsTrigger>
              <TabsTrigger value="attended" className="text-xs h-7 flex-1">Attended</TabsTrigger>
            </TabsList>
          </Tabs>
          <div className="relative mt-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              value={transferSearch}
              onChange={(e) => setTransferSearch(e.target.value)}
              placeholder="Search extension..."
              className="h-9 pl-9 text-xs rounded-xl"
              autoFocus
            />
          </div>
          <div className="mt-2 max-h-40 overflow-auto divide-y divide-border/30 rounded-xl">
            {transferTargets.slice(0, 10).map((ext) => (
              <button
                key={ext.id}
                className="flex items-center gap-2.5 w-full px-3 py-2.5 text-left hover:bg-accent/50 transition-colors"
                onClick={() => {
                  if (transferTab === "blind") {
                    blindTransfer(ext.extension_number)
                  } else {
                    startConsultTransfer(ext.extension_number)
                  }
                }}
              >
                <div className={cn(
                  "size-2.5 rounded-full",
                  STATUS_CONFIG[getExtensionStatus(ext)].dot
                )} />
                <span className="font-mono text-xs font-bold">{ext.extension_number}</span>
                <span className="text-[11px] text-muted-foreground truncate">
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

// ── Extension Directory ─────────────────────────────────────────────
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
    <SectionCard
      icon={Users}
      title="Extensions"
      accent="indigo"
      badge={
        <Badge variant="secondary" className="h-5 min-w-[22px] px-1.5 text-[10px] font-bold font-mono">
          {filteredExtensions.length}
        </Badge>
      }
      className="flex-1"
    >
      <div className="p-3 space-y-2">
        {isMsp && tenants && tenants.length > 1 && (
          <Select
            value={selectedTenantId ?? "__current__"}
            onValueChange={(v) => setSelectedTenantId(v === "__current__" ? null : v)}
          >
            <SelectTrigger className="h-8 text-xs rounded-xl">
              <Building2 className="h-3.5 w-3.5 mr-1.5 text-muted-foreground" />
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
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search..."
            className="h-8 pl-9 text-xs rounded-xl border-border/40"
          />
        </div>
      </div>
      <div className="flex-1 overflow-auto p-3 pt-0 max-h-[400px]">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
          </div>
        ) : sortedExtensions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
            <Phone className="mb-2 h-5 w-5 text-[oklch(0.55_0.18_265_/_40%)]" />
            <span className="text-xs font-medium opacity-50">No extensions found</span>
          </div>
        ) : (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(76px,1fr))] gap-1.5">
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
    </SectionCard>
  )
}

// ── Queue Stats ─────────────────────────────────────────────────────
function QueueStatsPanel() {
  const { data: stats } = useQueueStats()

  if (!stats?.length) {
    return (
      <SectionCard icon={Headset} title="Queues" accent="teal">
        <div className="flex flex-col items-center justify-center py-6 text-muted-foreground">
          <Headset className="mb-2 h-5 w-5 text-[oklch(0.60_0.15_185_/_40%)]" />
          <span className="text-xs font-medium opacity-50">No queues</span>
        </div>
      </SectionCard>
    )
  }

  const totalWaiting = stats.reduce((a, q) => a + q.waiting_count, 0)

  return (
    <SectionCard
      icon={Headset}
      title="Queues"
      accent="teal"
      badge={totalWaiting > 0 ? (
        <Badge variant="destructive" className="h-5 min-w-[22px] px-1.5 text-[10px] font-bold font-mono">
          {totalWaiting}
        </Badge>
      ) : undefined}
    >
      <div className="divide-y divide-border/30">
        {stats.map((q) => (
          <div key={q.queue_id} className="px-4 py-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold truncate">{q.queue_name}</span>
              {q.waiting_count > 0 && (
                <Badge variant="destructive" className="h-5 px-1.5 text-[10px] font-bold font-mono">
                  {q.waiting_count}
                </Badge>
              )}
            </div>
            <div className="mt-1.5 flex gap-4 text-[11px] text-muted-foreground/70">
              <span className="flex items-center gap-1.5">
                <Users className="h-3 w-3" />
                {q.agents_available}/{q.agents_logged_in}
              </span>
              {q.longest_wait_seconds > 0 && (
                <span className="flex items-center gap-1.5">
                  <Clock className="h-3 w-3" />
                  {Math.floor(q.longest_wait_seconds / 60)}:{String(q.longest_wait_seconds % 60).padStart(2, "0")}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
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

  const handleExtensionClick = useCallback((extNumber: string) => {
    if (transferMode === "selecting") {
      blindTransfer(extNumber)
    } else if (isInCall) {
      startTransfer()
      setTimeout(() => {
        useSoftphoneStore.getState().blindTransfer(extNumber)
      }, 0)
    } else {
      makeCall(extNumber)
    }
  }, [transferMode, isInCall, blindTransfer, startTransfer, makeCall])

  const handlePickup = useCallback((slotNumber: number) => {
    if (callState === "idle") {
      makeCall(`*86${slotNumber}`)
    }
  }, [callState, makeCall])

  return (
    <>
      <audio ref={remoteAudioRef} autoPlay />
      <div className="flex h-[calc(100vh-3.5rem)] flex-col overflow-hidden bg-background relative">
        {/* Mesh gradient background */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -top-1/4 -right-1/4 w-[60%] h-[60%] rounded-full bg-[radial-gradient(circle,oklch(0.55_0.22_265_/_8%)_0%,transparent_70%)]" />
          <div className="absolute -bottom-1/4 -left-1/4 w-[50%] h-[50%] rounded-full bg-[radial-gradient(circle,oklch(0.60_0.16_185_/_6%)_0%,transparent_70%)]" />
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[40%] h-[40%] rounded-full bg-[radial-gradient(circle,oklch(0.55_0.18_300_/_5%)_0%,transparent_70%)]" />
        </div>
        {/* ── Top Bar ─────────────────────────────────────────── */}
        <div className="relative flex items-center gap-4 border-b border-border/60 bg-card/80 backdrop-blur-xl px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center size-8 rounded-xl bg-gradient-to-br from-[oklch(0.50_0.20_265)] to-[oklch(0.36_0.18_272)] shadow-[0_2px_8px_oklch(0.42_0.18_265_/_25%)]">
              <Phone className="size-4 text-white" />
            </div>
            <span className="text-sm font-bold tracking-tight">{t("softphone.title")}</span>
          </div>

          <div className="h-5 w-px bg-border/40" />

          {/* Registration status */}
          <span className={cn(
            "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider",
            status === "registered" && "bg-[oklch(0.62_0.19_155_/_10%)]",
            status === "connecting" && "bg-[oklch(0.72_0.16_75_/_10%)]",
            status === "disconnected" && "bg-muted/50",
            status === "error" && "bg-[oklch(0.58_0.22_25_/_10%)]",
          )}>
            <span className={cn(
              "size-1.5 rounded-full",
              status === "registered" && "bg-[var(--sp-call-green)]",
              status === "connecting" && "bg-[var(--sp-hold-amber)] animate-pulse",
              status === "disconnected" && "bg-zinc-400",
              status === "error" && "bg-[var(--sp-call-red)]",
            )} />
            <span className="text-muted-foreground capitalize">{status}</span>
          </span>

          <div className="flex-1" />
          <LiveClock />
        </div>

        {/* ── Main Content: 3-column dashboard ────────────────── */}
        <div className="flex flex-1 overflow-hidden">

          {/* ─── Left Column: Recent + Voicemail ────────────── */}
          <div className="flex w-[340px] shrink-0 flex-col border-r border-border/40 bg-card/40 overflow-hidden">
            <Tabs defaultValue="recent" className="flex flex-1 flex-col">
              <TabsList className="mx-4 mt-4 mb-1 h-10 w-auto">
                <TabsTrigger value="recent" className="text-xs h-8 gap-1.5 px-4 font-semibold">
                  <History className="h-3.5 w-3.5" />
                  {t("softphone.page.recent")}
                </TabsTrigger>
                <TabsTrigger value="voicemail" className="text-xs h-8 gap-1.5 px-4 font-semibold">
                  <Voicemail className="h-3.5 w-3.5" />
                  {t("softphone.page.voicemail")}
                </TabsTrigger>
              </TabsList>
              <TabsContent value="recent" className="flex-1 mt-0 overflow-auto">
                <RecentCallsList />
              </TabsContent>
              <TabsContent value="voicemail" className="flex-1 mt-0 overflow-auto">
                <VoicemailList />
              </TabsContent>
            </Tabs>
          </div>

          {/* ─── Center Column: Dialpad OR Active Call ───────── */}
          <div className="relative flex flex-1 flex-col items-center justify-center overflow-hidden px-8 py-6">
            {/* Ambient glow behind center content */}
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <div className="size-[600px] rounded-full bg-[radial-gradient(circle,oklch(0.50_0.20_265_/_12%)_0%,oklch(0.45_0.12_280_/_5%)_50%,transparent_75%)]" />
            </div>
            <div className="relative z-10 flex flex-col items-center justify-center flex-1 w-full">
            {isInCall ? (
              <ActiveCallDisplay />
            ) : (
              <CenterDialpad />
            )}
            </div>
          </div>

          {/* ─── Right Column: Extensions + Parking + Queues ── */}
          <div className="flex w-[340px] shrink-0 flex-col gap-3 overflow-auto border-l border-border/40 bg-card/40 p-3">
            <ExtensionDirectory onExtensionClick={handleExtensionClick} />
            <ParkingPanel onPickup={handlePickup} />
            <QueueStatsPanel />
          </div>
        </div>
      </div>
    </>
  )
}
