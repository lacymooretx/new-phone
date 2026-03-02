import { useRef } from "react"
import { useTranslation } from "react-i18next"
import { Phone, Minus, X, Settings } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
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

  // Collapsed: floating phone button
  if (!panelOpen) {
    return (
      <>
        <audio ref={remoteAudioRef} autoPlay />
        <div className="fixed bottom-4 right-4 z-50">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                onClick={togglePanel}
                size="icon"
                className={cn(
                  "size-12 rounded-full shadow-lg",
                  hasActiveCall
                    ? "bg-green-600 hover:bg-green-700 text-white animate-pulse"
                    : "bg-primary hover:bg-primary/90"
                )}
              >
                <Phone className="size-5" />
                <span
                  className={cn(
                    "absolute -top-0.5 -right-0.5 size-3 rounded-full border-2 border-background",
                    status === "registered" && "bg-green-500",
                    status === "connecting" && "bg-yellow-500",
                    status === "disconnected" && "bg-zinc-400",
                    status === "error" && "bg-red-500"
                  )}
                />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="left">{t('softphone.title')}</TooltipContent>
          </Tooltip>
        </div>
      </>
    )
  }

  // Minimized: small bar
  if (panelMinimized) {
    return (
      <>
        <audio ref={remoteAudioRef} autoPlay />
        <div className="fixed bottom-4 right-4 z-50 w-64 rounded-lg border bg-card text-card-foreground shadow-lg">
          <div
            className="flex items-center justify-between px-3 py-2 cursor-pointer"
            onClick={() => useSoftphoneStore.getState().expandPanel()}
          >
            <div className="flex items-center gap-2">
              <Phone className="size-4" />
              <RegistrationStatusIndicator status={status} />
            </div>
            <Button variant="ghost" size="icon" className="size-6" onClick={(e) => { e.stopPropagation(); togglePanel() }}>
              <X className="size-3" />
            </Button>
          </div>
        </div>
      </>
    )
  }

  // Expanded panel
  return (
    <>
      <audio ref={remoteAudioRef} autoPlay />
      <div className="fixed bottom-4 right-4 z-50 w-80 rounded-lg border bg-card text-card-foreground shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-3 py-2">
          <div className="flex items-center gap-2">
            <Phone className="size-4" />
            <span className="text-sm font-medium">{t('softphone.title')}</span>
          </div>
          <div className="flex items-center gap-1">
            <RegistrationStatusIndicator status={status} />
            <Button variant="ghost" size="icon" className="size-6" onClick={minimizePanel}>
              <Minus className="size-3" />
            </Button>
            <Button variant="ghost" size="icon" className="size-6" onClick={togglePanel}>
              <X className="size-3" />
            </Button>
          </div>
        </div>

        {/* Body */}
        <div className="p-3 space-y-3">
          {callState === "ringing_in" && <IncomingCall />}
          {(callState === "ringing_out" || callState === "connected" || callState === "on_hold") && (
            <ActiveCall />
          )}
          <DialPad />
          <details className="group">
            <summary className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer select-none">
              <Settings className="size-3" />
              {t('softphone.audioDevices')}
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
