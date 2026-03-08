import { useTranslation } from "react-i18next"
import { Mic, MicOff, Pause, Play, PhoneOff, ParkingSquare } from "lucide-react"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useSoftphoneStore } from "@/stores/softphone-store"

function ControlButton({
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
            "flex items-center justify-center rounded-xl transition-all duration-200",
            "active:scale-90",
            large ? "size-12" : "size-11",
            destructive
              ? "bg-gradient-to-br from-[var(--sp-call-red)] to-[oklch(0.50_0.22_30)] text-white shadow-md shadow-[oklch(0.58_0.22_25_/_15%)] hover:shadow-lg hover:brightness-110"
              : active
                ? "bg-primary text-primary-foreground shadow-md shadow-[var(--sp-glow)] hover:brightness-110"
                : "bg-[var(--sp-surface)] text-foreground border border-border/40 hover:bg-accent hover:border-border/60",
          )}
        >
          {children}
        </button>
      </TooltipTrigger>
      <TooltipContent className="font-medium text-xs">{tooltip}</TooltipContent>
    </Tooltip>
  )
}

export function CallControls() {
  const { t } = useTranslation()
  const { isMuted, isOnHold, callState, toggleMute, toggleHold, hangup, sendDTMF } = useSoftphoneStore()

  return (
    <div className="flex items-center justify-center gap-2 mt-1">
      <ControlButton onClick={toggleMute} active={isMuted} tooltip={isMuted ? t('softphone.unmute') : t('softphone.mute')}>
        {isMuted ? <MicOff className="size-4.5" /> : <Mic className="size-4.5" />}
      </ControlButton>

      <ControlButton onClick={toggleHold} active={isOnHold} tooltip={isOnHold ? t('softphone.resume') : t('softphone.hold')}>
        {isOnHold ? <Play className="size-4.5" /> : <Pause className="size-4.5" />}
      </ControlButton>

      {callState === "connected" && (
        <ControlButton onClick={() => sendDTMF("*85")} tooltip={t('softphone.park')}>
          <ParkingSquare className="size-4.5" />
        </ControlButton>
      )}

      <ControlButton onClick={hangup} destructive large tooltip={t('softphone.hangUp')}>
        <PhoneOff className="size-5" />
      </ControlButton>
    </div>
  )
}
