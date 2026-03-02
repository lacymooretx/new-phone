import { useState, useEffect } from "react"
import { useTranslation } from "react-i18next"
import { Link, useNavigate } from "react-router"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { ConnectLogo } from "@/components/connect-logo"
import { useForgotPassword } from "@/api/auth"
import { useAuthStore } from "@/stores/auth-store"

export function ForgotPasswordPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  useEffect(() => {
    if (isAuthenticated) navigate("/", { replace: true })
  }, [isAuthenticated, navigate])

  const forgotPassword = useForgotPassword()
  const [email, setEmail] = useState("")
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await forgotPassword.mutateAsync({ email })
      setSubmitted(true)
    } catch (err: any) {
      setError(err?.detail || err?.message || t('auth.somethingWentWrong'))
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/50 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2">
            <ConnectLogo className="h-12 w-12" />
          </div>
          <CardTitle className="text-2xl">{t('common.appName')}</CardTitle>
          <CardDescription>{t('auth.forgotPasswordTitle')}</CardDescription>
        </CardHeader>
        <CardContent>
          {submitted ? (
            <div className="space-y-4 text-center">
              <p className="text-sm text-green-600">
                {t('auth.resetLinkSent')}
              </p>
              <Link to="/login" className="text-sm text-muted-foreground hover:text-foreground">
                {t('auth.backToLogin')}
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">{t('auth.email')}</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="admin@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoFocus
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" disabled={forgotPassword.isPending}>
                {forgotPassword.isPending ? t('auth.sending') : t('auth.sendResetLink')}
              </Button>
              <div className="text-center">
                <Link to="/login" className="text-sm text-muted-foreground hover:text-foreground">
                  {t('auth.backToLogin')}
                </Link>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
