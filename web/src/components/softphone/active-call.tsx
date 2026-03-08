import { useTranslation } from "react-i18next"
import { cn } from "@/lib/utils"
import { useSoftphoneStore } from "@/stores/softphone-store"
import { useCallTimer } from "@/hooks/use-call-timer"
import { CallControls } from "./call-controls"

export function ActiveCall() {
  const { t } = useTranslation()
  const { callState, remoteIdentity, callStartTime } = useSoftphoneStore()
  const elapsed = useCallTimer(callStartTime)

  const initial = remoteIdentity?.charAt(0)?.toUpperCase() || "?"
  const isOnHold = callState === "on_hold"
  const isRinging = callState === "ringing_out"

  return (
    <div className="flex flex-col items-center gap-3 py-4 sp-animate-in">
      {/* Avatar */}
      <div className="relative">
        <div className={cn(
          "flex items-center justify-center size-16 rounded-2xl text-xl font-bold",
          "transition-all duration-300",
          isOnHold
            ? "bg-gradient-to-br from-[var(--sp-hold-amber)] to-[oklch(0.65_0.14_85)] text-white"
            : "bg-gradient-to-br from-[oklch(0.50_0.20_265)] to-[oklch(0.40_0.18_275)] text-white",
          isRinging && "animate-[sp-ring-pulse_1.5s_ease-in-out_infinite]",
        )}>
          {initial}
        </div>
        {isRinging && (
          <span className="absolute inset-0 rounded-2xl border-2 border-primary/40 animate-ping" />
        )}
      </div>

      {/* Call info */}
      <div className="text-center">
        <p className="text-lg font-bold tracking-tight">{remoteIdentity || t('softphone.unknown')}</p>
        <div className="flex items-center justify-center gap-2 mt-1">
          {isRinging && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider bg-primary/10 text-primary">
              <span className="size-1.5 rounded-full bg-primary animate-pulse" />
              {t('softphone.ringing')}
            </span>
          )}
          {isOnHold && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider bg-[oklch(0.72_0.16_75_/_15%)] text-[var(--sp-hold-amber)]">
              <span className="size-1.5 rounded-full bg-[var(--sp-hold-amber)]" />
              {t('softphone.onHold')}
            </span>
          )}
          {callState === "connected" && elapsed && (
            <span className="text-sm font-mono text-muted-foreground tabular-nums">{elapsed}</span>
          )}
        </div>
      </div>

      {/* Controls */}
      <CallControls />
    </div>
  )
}
