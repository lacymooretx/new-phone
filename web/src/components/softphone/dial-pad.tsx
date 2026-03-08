import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Phone, Delete } from "lucide-react"
import { cn } from "@/lib/utils"
import { useSoftphoneStore } from "@/stores/softphone-store"

const KEYS: Array<{ digit: string; letters: string }> = [
  { digit: "1", letters: "" },
  { digit: "2", letters: "ABC" },
  { digit: "3", letters: "DEF" },
  { digit: "4", letters: "GHI" },
  { digit: "5", letters: "JKL" },
  { digit: "6", letters: "MNO" },
  { digit: "7", letters: "PQRS" },
  { digit: "8", letters: "TUV" },
  { digit: "9", letters: "WXYZ" },
  { digit: "*", letters: "" },
  { digit: "0", letters: "+" },
  { digit: "#", letters: "" },
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

  const handleBackspace = () => {
    setNumber((prev) => prev.slice(0, -1))
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
    <div className="flex flex-col gap-2.5">
      {/* Number display */}
      <div className="relative">
        <input
          value={number}
          onChange={(e) => setNumber(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t('softphone.enterNumber')}
          className={cn(
            "w-full text-center text-xl font-semibold tracking-wider h-12 rounded-xl",
            "bg-[var(--sp-surface)] border border-border/50",
            "placeholder:text-muted-foreground/40 placeholder:text-base placeholder:font-normal placeholder:tracking-normal",
            "focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50",
            "transition-all duration-200",
          )}
        />
        {number && (
          <button
            onClick={handleBackspace}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
          >
            <Delete className="size-4.5" />
          </button>
        )}
      </div>

      {/* Dial pad grid */}
      <div className="grid grid-cols-3 gap-1.5">
        {KEYS.map(({ digit, letters }) => (
          <button
            key={digit}
            onClick={() => handleKey(digit)}
            className={cn(
              "sp-dial-btn relative flex flex-col items-center justify-center",
              "h-14 rounded-xl",
              "bg-[var(--sp-surface)] hover:bg-accent",
              "border border-transparent hover:border-border/50",
              "transition-all duration-150",
              "active:bg-accent/80",
              "group",
            )}
          >
            <span className="text-lg font-semibold leading-none text-foreground">
              {digit}
            </span>
            {letters && (
              <span className="text-[9px] font-medium tracking-[0.15em] text-muted-foreground/60 mt-0.5 leading-none">
                {letters}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Call button */}
      {!inCall && (
        <button
          onClick={handleCall}
          disabled={!number.trim() || callState !== "idle"}
          className={cn(
            "flex items-center justify-center gap-2 h-12 rounded-xl font-semibold text-sm",
            "bg-gradient-to-r from-[var(--sp-call-green)] to-[oklch(0.58_0.17_165)]",
            "text-white shadow-md shadow-[oklch(0.62_0.19_155_/_20%)]",
            "hover:shadow-lg hover:shadow-[oklch(0.62_0.19_155_/_30%)] hover:brightness-105",
            "active:scale-[0.98] active:brightness-95",
            "disabled:opacity-40 disabled:shadow-none disabled:pointer-events-none",
            "transition-all duration-200",
          )}
        >
          <Phone className="size-4.5" />
          {t('softphone.call')}
        </button>
      )}
    </div>
  )
}
