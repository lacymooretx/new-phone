import { useState, useEffect } from "react"
import { useTranslation } from "react-i18next"
import { Link, useSearchParams, useNavigate } from "react-router"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Phone } from "lucide-react"
import { useResetPassword } from "@/api/auth"
import { useAuthStore } from "@/stores/auth-store"

export function ResetPasswordPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  useEffect(() => {
    if (isAuthenticated) navigate("/", { replace: true })
  }, [isAuthenticated, navigate])

  const [params] = useSearchParams()
  const token = params.get("token")
  const resetPassword = useResetPassword()

  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/50 p-4">
        <Card className="w-full max-w-sm">
          <CardHeader className="text-center">
            <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary">
              <Phone className="h-6 w-6 text-primary-foreground" />
            </div>
            <CardTitle className="text-2xl">{t('common.appName')}</CardTitle>
            <CardDescription>{t('auth.passwordReset')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-center">
            <p className="text-sm text-destructive">{t('auth.invalidResetLink')}</p>
            <Link to="/login" className="text-sm text-muted-foreground hover:text-foreground">
              {t('auth.backToLogin')}
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (newPassword.length < 8) {
      setError(t('validation.passwordMinLength'))
      return
    }

    if (newPassword !== confirmPassword) {
      setError(t('validation.passwordMismatch'))
      return
    }

    try {
      await resetPassword.mutateAsync({ token, new_password: newPassword })
      setSuccess(true)
    } catch (err: any) {
      setError(err?.detail || err?.message || t('auth.failedToResetPassword'))
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/50 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary">
            <Phone className="h-6 w-6 text-primary-foreground" />
          </div>
          <CardTitle className="text-2xl">{t('common.appName')}</CardTitle>
          <CardDescription>{t('auth.resetYourPassword')}</CardDescription>
        </CardHeader>
        <CardContent>
          {success ? (
            <div className="space-y-4 text-center">
              <p className="text-sm text-green-600">{t('auth.passwordResetSuccess')}</p>
              <Link to="/login" className="text-sm text-muted-foreground hover:text-foreground">
                {t('auth.backToLogin')}
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="new-password">{t('auth.newPassword')}</Label>
                <Input
                  id="new-password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                  autoFocus
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm-password">{t('auth.confirmPassword')}</Label>
                <Input
                  id="confirm-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={8}
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" disabled={resetPassword.isPending}>
                {resetPassword.isPending ? t('auth.resetting') : t('auth.resetPassword')}
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
