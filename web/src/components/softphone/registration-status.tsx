import i18next from "i18next"
import { Headphones } from "lucide-react"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useHeadsetStore } from "@/stores/headset-store"
import type { RegistrationStatus } from "@/lib/sip-client"

const statusConfig: Record<RegistrationStatus, { color: string; bg: string }> = {
  registered: { color: "bg-[var(--sp-call-green)]", bg: "bg-[oklch(0.62_0.19_155_/_12%)]" },
  connecting: { color: "bg-[var(--sp-hold-amber)] animate-pulse", bg: "bg-[oklch(0.72_0.16_75_/_12%)]" },
  disconnected: { color: "bg-zinc-400 dark:bg-zinc-500", bg: "bg-muted" },
  error: { color: "bg-[var(--sp-call-red)]", bg: "bg-[oklch(0.58_0.22_25_/_10%)]" },
}

const statusKeys: Record<RegistrationStatus, string> = {
  registered: "softphone.status.registered",
  connecting: "softphone.status.connecting",
  disconnected: "softphone.status.disconnected",
  error: "softphone.status.error",
}

export function RegistrationStatusIndicator({ status }: { status: RegistrationStatus }) {
  const { isConnected, deviceName, vendorName } = useHeadsetStore()

  return (
    <div className="flex items-center gap-2">
      <span className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider",
        statusConfig[status].bg,
      )}>
        <span className={cn("size-1.5 rounded-full", statusConfig[status].color)} />
        <span className="text-muted-foreground">{i18next.t(statusKeys[status])}</span>
      </span>
      {isConnected && (
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="relative flex items-center">
              <Headphones className="size-3.5 text-muted-foreground" />
              <span className="absolute -top-0.5 -right-0.5 size-1.5 rounded-full bg-[var(--sp-call-green)]" />
            </span>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="text-xs">
            {deviceName ?? i18next.t("softphone.headset.connected")}
            {vendorName && <span className="text-muted-foreground"> ({vendorName})</span>}
          </TooltipContent>
        </Tooltip>
      )}
    </div>
  )
}
