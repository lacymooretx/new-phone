import { useTranslation } from "react-i18next"
import { Phone, PhoneOff } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useSoftphoneStore } from "@/stores/softphone-store"

export function IncomingCall() {
  const { t } = useTranslation()
  const { remoteIdentity, answerCall, declineCall } = useSoftphoneStore()

  return (
    <div className="flex flex-col items-center gap-4 py-4">
      <div className="relative">
        <div className="size-16 rounded-full bg-green-500/20 flex items-center justify-center animate-pulse">
          <Phone className="size-8 text-green-500" />
        </div>
      </div>
      <div className="text-center">
        <p className="text-sm text-muted-foreground">{t('softphone.incomingCall')}</p>
        <p className="text-lg font-semibold font-mono">{remoteIdentity || t('softphone.unknown')}</p>
      </div>
      <div className="flex items-center gap-4">
        <Button
          variant="destructive"
          size="icon"
          className="size-12 rounded-full"
          onClick={declineCall}
        >
          <PhoneOff className="size-5" />
        </Button>
        <Button
          size="icon"
          className="size-12 rounded-full bg-green-600 hover:bg-green-700 text-white"
          onClick={answerCall}
        >
          <Phone className="size-5" />
        </Button>
      </div>
    </div>
  )
}
