import { useTranslation } from "react-i18next"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { LoginForm } from "./login-form"
import { ConnectLogo } from "@/components/connect-logo"

export function LoginPage() {
  const { t } = useTranslation()
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/50 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2">
            <ConnectLogo className="h-12 w-12" />
          </div>
          <CardTitle className="text-2xl">{t('common.appName')}</CardTitle>
          <CardDescription>{t('auth.signInToAccount')}</CardDescription>
        </CardHeader>
        <CardContent>
          <LoginForm />
        </CardContent>
      </Card>
    </div>
  )
}
