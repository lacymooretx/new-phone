import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"

interface MfaFormProps {
  onSubmit: (code: string) => void
  onBack?: () => void
  isLoading: boolean
  error?: string | null
}

export function MfaForm({ onSubmit, onBack, isLoading, error }: MfaFormProps) {
  const { t } = useTranslation()
  const [code, setCode] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (code.length === 6) onSubmit(code)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="mfa-code">{t('auth.authenticationCode')}</Label>
        <Input
          id="mfa-code"
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          maxLength={6}
          placeholder="000000"
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
          className="text-center text-2xl tracking-widest"
          autoFocus
        />
        <p className="text-sm text-muted-foreground">
          {t('auth.mfaCodeDescription')}
        </p>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit" className="w-full" disabled={isLoading || code.length !== 6}>
        {isLoading ? t('auth.verifying') : t('auth.verify')}
      </Button>
      {onBack && (
        <Button type="button" variant="ghost" className="w-full" onClick={onBack}>
          {t('auth.backToLogin')}
        </Button>
      )}
    </form>
  )
}
