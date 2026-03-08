import { useRef } from "react"
import { useTranslation } from "react-i18next"
import { Phone, Minus, X, ChevronUp, Settings } from "lucide-react"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useSoftphoneStore } from "@/stores/softphone-store"
import { useSoftphoneInit } from "@/hooks/use-softphone-init"
import { useHeadset } from "@/hooks/use-headset"
import { RegistrationStatusIndicator } from "./registration-status"
import { DialPad } from "./dial-pad"
import { IncomingCall } from "./incoming-call"
import { ActiveCall } from "./active-call"
import { AudioDeviceSelector } from "./audio-device-selector"

export function SoftphonePanel() {
  const { t } = useTranslation()
  const remoteAudioRef = useRef<HTMLAudioElement>(null)
  const { status } = useSoftphoneInit(remoteAudioRef)
  useHeadset()
  const {
    callState,
    panelOpen,
    panelMinimized,
    togglePanel,
    minimizePanel,
  } = useSoftphoneStore()

  const hasActiveCall = callState !== "idle"
  const isRinging = callState === "ringing_in"

  // Collapsed: floating phone FAB
  if (!panelOpen) {
    return (
      <>
        <audio ref={remoteAudioRef} autoPlay />
        <div className="fixed bottom-5 right-5 z-50">
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={togglePanel}
                className={cn(
                  "relative flex items-center justify-center size-14 rounded-2xl shadow-lg transition-all duration-300",
                  "bg-gradient-to-br from-[oklch(0.50_0.20_265)] to-[oklch(0.38_0.18_270)]",
                  "hover:shadow-xl hover:shadow-[var(--sp-glow)] hover:scale-105",
                  "active:scale-95",
                  hasActiveCall && "from-[oklch(0.58_0.19_155)] to-[oklch(0.48_0.19_160)]",
                  isRinging && "animate-[sp-ring-pulse_1.5s_ease-in-out_infinite]",
                )}
              >
                <Phone className="size-5.5 text-white" />
                {/* Status dot */}
                <span
                  className={cn(
                    "absolute -top-0.5 -right-0.5 size-3.5 rounded-full border-2 border-background transition-colors",
                    status === "registered" && "bg-[var(--sp-call-green)]",
                    status === "connecting" && "bg-[var(--sp-hold-amber)] animate-pulse",
                    status === "disconnected" && "bg-zinc-400",
                    status === "error" && "bg-[var(--sp-call-red)]"
                  )}
                />
                {/* Ringing ripple */}
                {isRinging && (
                  <>
                    <span className="absolute inset-0 rounded-2xl bg-[var(--sp-call-green)] animate-[sp-ripple_1.5s_ease-out_infinite]" />
                    <span className="absolute inset-0 rounded-2xl bg-[var(--sp-call-green)] animate-[sp-ripple_1.5s_ease-out_0.5s_infinite]" />
                  </>
                )}
              </button>
            </TooltipTrigger>
            <TooltipContent side="left" className="font-medium">{t('softphone.title')}</TooltipContent>
          </Tooltip>
        </div>
      </>
    )
  }

  // Minimized: slim bar
  if (panelMinimized) {
    return (
      <>
        <audio ref={remoteAudioRef} autoPlay />
        <div className="fixed bottom-5 right-5 z-50 sp-glass-panel rounded-2xl sp-animate-in">
          <div
            className="flex items-center gap-3 px-4 py-2.5 cursor-pointer select-none"
            onClick={() => useSoftphoneStore.getState().expandPanel()}
          >
            <div className="flex items-center gap-2.5">
              <div className={cn(
                "flex items-center justify-center size-8 rounded-xl",
                "bg-gradient-to-br from-[oklch(0.50_0.20_265)] to-[oklch(0.38_0.18_270)]",
                hasActiveCall && "from-[oklch(0.58_0.19_155)] to-[oklch(0.48_0.19_160)]",
              )}>
                <Phone className="size-3.5 text-white" />
              </div>
              <RegistrationStatusIndicator status={status} />
            </div>
            <div className="flex items-center gap-1 ml-2">
              <button
                className="flex items-center justify-center size-6 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                onClick={(e) => { e.stopPropagation(); useSoftphoneStore.getState().expandPanel() }}
              >
                <ChevronUp className="size-3.5" />
              </button>
              <button
                className="flex items-center justify-center size-6 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                onClick={(e) => { e.stopPropagation(); togglePanel() }}
              >
                <X className="size-3.5" />
              </button>
            </div>
          </div>
        </div>
      </>
    )
  }

  // Expanded panel
  return (
    <>
      <audio ref={remoteAudioRef} autoPlay />
      <div className="fixed bottom-5 right-5 z-50 w-[340px] sp-glass-panel rounded-2xl sp-animate-in">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2.5">
            <div className={cn(
              "flex items-center justify-center size-8 rounded-xl",
              "bg-gradient-to-br from-[oklch(0.50_0.20_265)] to-[oklch(0.38_0.18_270)]",
              hasActiveCall && "from-[oklch(0.58_0.19_155)] to-[oklch(0.48_0.19_160)]",
            )}>
              <Phone className="size-3.5 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-semibold tracking-tight">{t('softphone.title')}</span>
              <RegistrationStatusIndicator status={status} />
            </div>
          </div>
          <div className="flex items-center gap-0.5">
            <button
              className="flex items-center justify-center size-7 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent/80 transition-colors"
              onClick={minimizePanel}
            >
              <Minus className="size-3.5" />
            </button>
            <button
              className="flex items-center justify-center size-7 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent/80 transition-colors"
              onClick={togglePanel}
            >
              <X className="size-3.5" />
            </button>
          </div>
        </div>

        {/* Divider */}
        <div className="mx-3 h-px bg-border/60" />

        {/* Body */}
        <div className="p-3 space-y-3">
          {callState === "ringing_in" && <IncomingCall />}
          {(callState === "ringing_out" || callState === "connected" || callState === "on_hold") && (
            <ActiveCall />
          )}
          <DialPad />
          <details className="group">
            <summary className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer select-none hover:text-foreground transition-colors py-1">
              <Settings className="size-3.5" />
              <span className="font-medium">{t('softphone.audioDevices')}</span>
            </summary>
            <div className="pt-2">
              <AudioDeviceSelector />
            </div>
          </details>
        </div>
      </div>
    </>
  )
}
