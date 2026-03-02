import { useTranslation } from "react-i18next"
import { Badge } from "@/components/ui/badge"
import { useSoftphoneStore } from "@/stores/softphone-store"
import { useCallTimer } from "@/hooks/use-call-timer"
import { CallControls } from "./call-controls"

export function ActiveCall() {
  const { t } = useTranslation()
  const { callState, remoteIdentity, callStartTime } = useSoftphoneStore()
  const elapsed = useCallTimer(callStartTime)

  return (
    <div className="flex flex-col items-center gap-3 py-3">
      <div className="text-center">
        <p className="text-lg font-semibold font-mono">{remoteIdentity || t('softphone.unknown')}</p>
        {callState === "ringing_out" && (
          <Badge variant="secondary" className="mt-1">{t('softphone.ringing')}</Badge>
        )}
        {callState === "on_hold" && (
          <Badge variant="outline" className="mt-1 border-yellow-500 text-yellow-600">{t('softphone.onHold')}</Badge>
        )}
        {callState === "connected" && elapsed && (
          <p className="text-sm text-muted-foreground font-mono mt-1">{elapsed}</p>
        )}
      </div>
      {(callState === "connected" || callState === "on_hold") && <CallControls />}
      {callState === "ringing_out" && (
        <CallControls />
      )}
    </div>
  )
}
