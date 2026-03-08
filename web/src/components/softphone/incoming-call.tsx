import { useTranslation } from "react-i18next"
import { Phone, PhoneOff } from "lucide-react"
import { cn } from "@/lib/utils"
import { useSoftphoneStore } from "@/stores/softphone-store"

export function IncomingCall() {
  const { t } = useTranslation()
  const { remoteIdentity, answerCall, declineCall } = useSoftphoneStore()

  return (
    <div className="flex flex-col items-center gap-4 py-5 sp-animate-in">
      {/* Animated avatar with ripple rings */}
      <div className="relative flex items-center justify-center">
        {/* Ripple rings */}
        <span className="absolute size-24 rounded-full border-2 border-[var(--sp-call-green)] animate-[sp-ripple_2s_ease-out_infinite]" />
        <span className="absolute size-24 rounded-full border-2 border-[var(--sp-call-green)] animate-[sp-ripple_2s_ease-out_0.6s_infinite]" />
        <span className="absolute size-24 rounded-full border-2 border-[var(--sp-call-green)] animate-[sp-ripple_2s_ease-out_1.2s_infinite]" />
        {/* Avatar circle */}
        <div className={cn(
          "relative flex items-center justify-center size-20 rounded-full",
          "bg-gradient-to-br from-[oklch(0.62_0.19_155)] to-[oklch(0.50_0.17_165)]",
          "shadow-lg shadow-[oklch(0.62_0.19_155_/_25%)]",
          "animate-[sp-incoming-glow_2s_ease-in-out_infinite]",
        )}>
          <Phone className="size-8 text-white animate-[sp-ring-pulse_1s_ease-in-out_infinite]" />
        </div>
      </div>

      {/* Caller info */}
      <div className="text-center mt-2">
        <p className="text-xs font-medium text-[var(--sp-call-green)] uppercase tracking-wider mb-1">
          {t('softphone.incomingCall')}
        </p>
        <p className="text-xl font-bold tracking-tight">
          {remoteIdentity || t('softphone.unknown')}
        </p>
      </div>

      {/* Answer / Decline */}
      <div className="flex items-center gap-6 mt-2">
        <div className="flex flex-col items-center gap-1.5">
          <button
            onClick={declineCall}
            className={cn(
              "flex items-center justify-center size-14 rounded-full",
              "bg-gradient-to-br from-[var(--sp-call-red)] to-[oklch(0.50_0.22_30)]",
              "text-white shadow-md shadow-[oklch(0.58_0.22_25_/_20%)]",
              "hover:shadow-lg hover:brightness-110",
              "active:scale-95 active:brightness-90",
              "transition-all duration-200",
            )}
          >
            <PhoneOff className="size-5.5" />
          </button>
          <span className="text-[10px] font-medium text-muted-foreground">{t('softphone.reject')}</span>
        </div>
        <div className="flex flex-col items-center gap-1.5">
          <button
            onClick={answerCall}
            className={cn(
              "flex items-center justify-center size-14 rounded-full",
              "bg-gradient-to-br from-[var(--sp-call-green)] to-[oklch(0.50_0.17_165)]",
              "text-white shadow-md shadow-[oklch(0.62_0.19_155_/_20%)]",
              "hover:shadow-lg hover:brightness-110",
              "active:scale-95 active:brightness-90",
              "transition-all duration-200",
            )}
          >
            <Phone className="size-5.5" />
          </button>
          <span className="text-[10px] font-medium text-muted-foreground">{t('softphone.accept')}</span>
        </div>
      </div>
    </div>
  )
}
