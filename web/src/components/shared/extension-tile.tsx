import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import { type ExtStatus, STATUS_CONFIG } from "@/lib/extension-status"

export function ExtensionTile({
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
