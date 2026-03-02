import i18next from "i18next"
import { Headphones } from "lucide-react"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useHeadsetStore } from "@/stores/headset-store"
import type { RegistrationStatus } from "@/lib/sip-client"

const statusColors: Record<RegistrationStatus, string> = {
  registered: "bg-green-500",
  connecting: "bg-yellow-500",
  disconnected: "bg-zinc-400",
  error: "bg-red-500",
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
    <div className="flex items-center gap-1.5">
      <span className={cn("size-2 rounded-full", statusColors[status])} />
      <span className="text-xs text-muted-foreground">{i18next.t(statusKeys[status])}</span>
      {isConnected && (
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="relative ml-0.5 flex items-center">
              <Headphones className="size-3.5 text-muted-foreground" />
              <span className="absolute -top-0.5 -right-0.5 size-1.5 rounded-full bg-green-500" />
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
