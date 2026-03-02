import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Phone } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useSoftphoneStore } from "@/stores/softphone-store"

const KEYS = [
  ["1", "2", "3"],
  ["4", "5", "6"],
  ["7", "8", "9"],
  ["*", "0", "#"],
]

export function DialPad() {
  const { t } = useTranslation()
  const [number, setNumber] = useState("")
  const { callState, makeCall, sendDTMF } = useSoftphoneStore()
  const inCall = callState === "connected" || callState === "on_hold"

  const handleKey = (key: string) => {
    if (inCall) {
      sendDTMF(key)
    }
    setNumber((prev) => prev + key)
  }

  const handleCall = () => {
    if (!number.trim()) return
    makeCall(number.trim())
    setNumber("")
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault()
      handleCall()
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <Input
        value={number}
        onChange={(e) => setNumber(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t('softphone.enterNumber')}
        className="text-center text-lg font-mono"
      />
      <div className="grid grid-cols-3 gap-1">
        {KEYS.flat().map((key) => (
          <Button
            key={key}
            variant="outline"
            size="sm"
            className="h-10 text-base font-mono"
            onClick={() => handleKey(key)}
          >
            {key}
          </Button>
        ))}
      </div>
      {!inCall && (
        <Button
          onClick={handleCall}
          disabled={!number.trim() || callState !== "idle"}
          className="bg-green-600 hover:bg-green-700 text-white"
        >
          <Phone className="size-4 mr-1" />
          {t('softphone.call')}
        </Button>
      )}
    </div>
  )
}
