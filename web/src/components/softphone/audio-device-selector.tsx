import { useCallback, useEffect, useRef } from "react"
import { useTranslation } from "react-i18next"
import { Mic, Volume2, Headphones } from "lucide-react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useAudioDevices } from "@/hooks/use-audio-devices"
import { useHeadsetStore } from "@/stores/headset-store"
import { useSoftphoneStore } from "@/stores/softphone-store"

export function AudioDeviceSelector() {
  const { t } = useTranslation()
  const { microphones, speakers, selectedMic, selectedSpeaker, setSelectedMic, setSelectedSpeaker } =
    useAudioDevices()
  const { isConnected, deviceName, vendorName } = useHeadsetStore()
  const { setMicDevice, setSpeakerDevice } = useSoftphoneStore()

  const handleMicChange = useCallback((deviceId: string) => {
    setSelectedMic(deviceId)
    setMicDevice(deviceId)
  }, [setSelectedMic, setMicDevice])

  const handleSpeakerChange = useCallback((deviceId: string) => {
    setSelectedSpeaker(deviceId)
    setSpeakerDevice(deviceId)
  }, [setSelectedSpeaker, setSpeakerDevice])

  // Sync initial device selection to SIP client
  const syncedRef = useRef(false)
  useEffect(() => {
    if (syncedRef.current) return
    if (selectedMic) {
      setMicDevice(selectedMic)
      syncedRef.current = true
    }
  }, [selectedMic, setMicDevice])

  useEffect(() => {
    if (selectedSpeaker) {
      setSpeakerDevice(selectedSpeaker)
    }
  }, [selectedSpeaker, setSpeakerDevice])

  if (microphones.length === 0 && speakers.length === 0) {
    return <p className="text-xs text-muted-foreground">{t('softphone.noAudioDevices')}</p>
  }

  return (
    <div className="flex flex-col gap-2">
      {isConnected && (
        <div className="flex items-center gap-2 rounded-md bg-muted/50 px-2 py-1.5">
          <Headphones className="size-3.5 shrink-0 text-green-600" />
          <span className="text-xs text-muted-foreground">
            {deviceName ?? t("softphone.headset.connected")}
            {vendorName && (
              <span className="ml-1 rounded bg-muted px-1 py-0.5 text-[10px] font-medium">
                {vendorName}
              </span>
            )}
          </span>
        </div>
      )}
      {microphones.length > 0 && (
        <div className="flex items-center gap-2">
          <Mic className="size-3.5 shrink-0 text-muted-foreground" />
          <Select value={selectedMic} onValueChange={handleMicChange}>
            <SelectTrigger size="sm" className="h-7 text-xs flex-1">
              <SelectValue placeholder={t('softphone.microphone')} />
            </SelectTrigger>
            <SelectContent>
              {microphones.map((d) => (
                <SelectItem key={d.deviceId} value={d.deviceId} className="text-xs">
                  {d.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
      {speakers.length > 0 && (
        <div className="flex items-center gap-2">
          <Volume2 className="size-3.5 shrink-0 text-muted-foreground" />
          <Select value={selectedSpeaker} onValueChange={handleSpeakerChange}>
            <SelectTrigger size="sm" className="h-7 text-xs flex-1">
              <SelectValue placeholder={t('softphone.speaker')} />
            </SelectTrigger>
            <SelectContent>
              {speakers.map((d) => (
                <SelectItem key={d.deviceId} value={d.deviceId} className="text-xs">
                  {d.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
    </div>
  )
}
