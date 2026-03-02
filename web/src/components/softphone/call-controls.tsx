import { useTranslation } from "react-i18next"
import { Mic, MicOff, Pause, Play, PhoneOff, ParkingSquare } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useSoftphoneStore } from "@/stores/softphone-store"

export function CallControls() {
  const { t } = useTranslation()
  const { isMuted, isOnHold, callState, toggleMute, toggleHold, hangup, sendDTMF } = useSoftphoneStore()

  const handlePark = () => {
    // Send *85 DTMF to park the current call
    sendDTMF("*85")
  }

  return (
    <div className="flex items-center justify-center gap-2">
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={isMuted ? "destructive" : "outline"}
            size="icon"
            className="size-10 rounded-full"
            onClick={toggleMute}
          >
            {isMuted ? <MicOff className="size-4" /> : <Mic className="size-4" />}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{isMuted ? t('softphone.unmute') : t('softphone.mute')}</TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={isOnHold ? "default" : "outline"}
            size="icon"
            className="size-10 rounded-full"
            onClick={toggleHold}
          >
            {isOnHold ? <Play className="size-4" /> : <Pause className="size-4" />}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{isOnHold ? t('softphone.resume') : t('softphone.hold')}</TooltipContent>
      </Tooltip>

      {callState === "connected" && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              className="size-10 rounded-full"
              onClick={handlePark}
            >
              <ParkingSquare className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t('softphone.park')}</TooltipContent>
        </Tooltip>
      )}

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
        <TooltipContent>{t('softphone.hangUp')}</TooltipContent>
      </Tooltip>
    </div>
  )
}
