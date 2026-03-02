import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { useQueryClient } from "@tanstack/react-query"
import { useAuthStore } from "@/stores/auth-store"
import { useUsers, useUpdateUser } from "@/api/users"
import { useChangePassword, useSetupMfa, useConfirmMfa, useDisableMfa } from "@/api/auth"
import { queryKeys } from "@/api/query-keys"
import { PageHeader } from "@/components/shared/page-header"
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"
import { Shield, ShieldCheck } from "lucide-react"
import { toast } from "sonner"

const profileSchema = z.object({
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().min(1, "Last name is required"),
})

type ProfileFormValues = z.infer<typeof profileSchema>

export function ProfilePage() {
  const { t } = useTranslation()
  const { user: authUser } = useAuthStore()
  const language = useAuthStore((s) => s.language)
  const { setLanguage } = useAuthStore()
  const activeTenantId = useAuthStore((s) => s.activeTenantId)!
  const { data: users, isLoading } = useUsers()
  const updateMutation = useUpdateUser()
  const queryClient = useQueryClient()

  const currentUser = users?.find((u) => u.id === authUser?.id)

  const form = useForm<ProfileFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(profileSchema) as any,
    defaultValues: {
      first_name: "",
      last_name: "",
    },
  })

  useEffect(() => {
    if (currentUser) {
      form.reset({
        first_name: currentUser.first_name,
        last_name: currentUser.last_name,
      })
    }
  }, [currentUser, form])

  const onSubmit = (data: ProfileFormValues) => {
    if (!currentUser) return
    updateMutation.mutate(
      { id: currentUser.id, ...data },
      {
        onSuccess: () => toast.success(t('profile.profileUpdated')),
        onError: (err) => toast.error(err.message),
      }
    )
  }

  const roleLabel = currentUser?.role
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase()) ?? ""

  // --- Password Change ---
  const changePasswordMutation = useChangePassword()
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false)
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [passwordError, setPasswordError] = useState("")

  const handlePasswordSubmit = () => {
    setPasswordError("")
    if (newPassword.length < 8) {
      setPasswordError(t('validation.passwordMinLength'))
      return
    }
    if (newPassword !== confirmPassword) {
      setPasswordError(t('validation.passwordMismatch'))
      return
    }
    changePasswordMutation.mutate(
      { current_password: currentPassword, new_password: newPassword },
      {
        onSuccess: () => {
          toast.success(t('profile.passwordChanged'))
          setPasswordDialogOpen(false)
          setCurrentPassword("")
          setNewPassword("")
          setConfirmPassword("")
        },
        onError: (err) => toast.error(err.message),
      }
    )
  }

  // --- MFA Setup ---
  const setupMfaMutation = useSetupMfa()
  const confirmMfaMutation = useConfirmMfa()
  const disableMfaMutation = useDisableMfa()

  const [mfaSetupDialogOpen, setMfaSetupDialogOpen] = useState(false)
  const [mfaTotpUri, setMfaTotpUri] = useState("")
  const [mfaBackupCodes, setMfaBackupCodes] = useState<string[]>([])
  const [mfaCode, setMfaCode] = useState("")
  const [mfaSetupStep, setMfaSetupStep] = useState<"code" | "backup">("code")

  const [mfaDisableDialogOpen, setMfaDisableDialogOpen] = useState(false)
  const [mfaDisablePassword, setMfaDisablePassword] = useState("")

  const handleEnableMfa = () => {
    setupMfaMutation.mutate(undefined, {
      onSuccess: (data) => {
        setMfaTotpUri(data.totp_uri)
        setMfaBackupCodes(data.backup_codes)
        setMfaSetupStep("code")
        setMfaCode("")
        setMfaSetupDialogOpen(true)
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleConfirmMfa = () => {
    confirmMfaMutation.mutate(
      { code: mfaCode },
      {
        onSuccess: () => {
          toast.success(t('profile.mfaEnabledSuccess'))
          setMfaSetupStep("backup")
          void queryClient.invalidateQueries({ queryKey: queryKeys.users.list(activeTenantId) })
        },
        onError: (err) => toast.error(err.message),
      }
    )
  }

  const handleDisableMfa = () => {
    disableMfaMutation.mutate(
      { password: mfaDisablePassword },
      {
        onSuccess: () => {
          toast.success(t('profile.mfaDisabled'))
          setMfaDisableDialogOpen(false)
          setMfaDisablePassword("")
          void queryClient.invalidateQueries({ queryKey: queryKeys.users.list(activeTenantId) })
        },
        onError: (err) => toast.error(err.message),
      }
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('profile.title')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('profile.title') }]} />
        <Skeleton className="h-64 max-w-lg" />
      </div>
    )
  }

  if (!currentUser) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('profile.title')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('profile.title') }]} />
        <p className="text-muted-foreground">{t('profile.unableToLoad')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader title={t('profile.title')} description={t('profile.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('profile.title') }]} />

      <div className="grid gap-6 max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle>{t('profile.personalInfo')}</CardTitle>
            <CardDescription>{t('profile.personalInfoDescription')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <FormField
                    control={form.control}
                    name="first_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('profile.firstName')}</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="last_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('profile.lastName')}</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">{t('profile.emailLabel')}</label>
                  <Input value={currentUser.email} disabled />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">{t('profile.roleLabel')}</label>
                  <div>
                    <Badge variant="secondary">{roleLabel}</Badge>
                  </div>
                </div>

                <Button type="submit" disabled={updateMutation.isPending}>
                  {updateMutation.isPending ? t('common.saving') : t('profile.saveChanges')}
                </Button>
              </form>
            </Form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('profile.security')}</CardTitle>
            <CardDescription>{t('profile.securityDescription')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Password Section */}
            <div>
              <h4 className="text-sm font-medium mb-2">{t('profile.passwordSection')}</h4>
              <Button variant="outline" onClick={() => setPasswordDialogOpen(true)}>
                {t('profile.changePassword')}
              </Button>
            </div>

            <Separator />

            {/* MFA Section */}
            <div>
              <h4 className="text-sm font-medium mb-2">{t('profile.mfa')}</h4>
              {currentUser.mfa_enabled ? (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <ShieldCheck className="h-5 w-5 text-green-600 dark:text-green-400" />
                    <div>
                      <p className="text-sm font-medium">{t('profile.mfaEnabled')}</p>
                      <p className="text-xs text-muted-foreground">{t('profile.mfaEnabledDescription')}</p>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive"
                    onClick={() => setMfaDisableDialogOpen(true)}
                  >
                    {t('profile.disableMfa')}
                  </Button>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Shield className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">{t('profile.mfaNotEnabled')}</p>
                      <p className="text-xs text-muted-foreground">{t('profile.mfaNotEnabledDescription')}</p>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleEnableMfa}
                    disabled={setupMfaMutation.isPending}
                  >
                    {setupMfaMutation.isPending ? t('profile.settingUp') : t('profile.enableMfa')}
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>{t('profile.language')}</CardTitle>
            <CardDescription>{t('profile.languageDescription')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Select
              value={language}
              onValueChange={(lang) => {
                if (!currentUser) return
                updateMutation.mutate(
                  { id: currentUser.id, language: lang } as any,
                  {
                    onSuccess: () => {
                      setLanguage(lang)
                      toast.success(t('profile.languageUpdated'))
                    },
                    onError: (err) => toast.error(err.message),
                  }
                )
              }}
            >
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="en">{t('languages.en')}</SelectItem>
                <SelectItem value="es">{t('languages.es')}</SelectItem>
                <SelectItem value="fr">{t('languages.fr')}</SelectItem>
              </SelectContent>
            </Select>
          </CardContent>
        </Card>
      </div>

      {/* Password Change Dialog */}
      <Dialog open={passwordDialogOpen} onOpenChange={(open) => {
        setPasswordDialogOpen(open)
        if (!open) {
          setCurrentPassword("")
          setNewPassword("")
          setConfirmPassword("")
          setPasswordError("")
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('profile.changePassword')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('profile.currentPassword')}</label>
              <Input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('profile.newPassword')}</label>
              <Input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('profile.confirmNewPassword')}</label>
              <Input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </div>
            {passwordError && (
              <p className="text-sm text-destructive">{passwordError}</p>
            )}
            <Button
              onClick={handlePasswordSubmit}
              disabled={changePasswordMutation.isPending}
              className="w-full"
            >
              {changePasswordMutation.isPending ? t('profile.changingPassword') : t('profile.changePassword')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* MFA Setup Dialog */}
      <Dialog open={mfaSetupDialogOpen} onOpenChange={(open) => {
        if (!open && mfaSetupStep === "backup") {
          setMfaSetupDialogOpen(false)
          return
        }
        if (!open) {
          setMfaSetupDialogOpen(false)
          setMfaCode("")
          setMfaTotpUri("")
          setMfaBackupCodes([])
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {mfaSetupStep === "code" ? t('profile.setupMfa') : t('profile.backupCodes')}
            </DialogTitle>
          </DialogHeader>
          {mfaSetupStep === "code" ? (
            <div className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground mb-2">
                  {t('profile.copyTotpUri')}
                </p>
                <code className="block break-all bg-muted p-2 rounded text-xs">
                  {mfaTotpUri}
                </code>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-2">
                  {t('profile.enterMfaCode')}
                </p>
                <Input
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                  placeholder="000000"
                  maxLength={6}
                />
              </div>
              <Button
                onClick={handleConfirmMfa}
                disabled={confirmMfaMutation.isPending || mfaCode.length !== 6}
                className="w-full"
              >
                {confirmMfaMutation.isPending ? t('profile.confirming') : t('common.confirm')}
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                {t('profile.saveBackupCodes')}
              </p>
              <code className="block bg-muted p-3 rounded text-xs space-y-1">
                {mfaBackupCodes.map((code) => (
                  <div key={code}>{code}</div>
                ))}
              </code>
              <Button
                onClick={() => setMfaSetupDialogOpen(false)}
                className="w-full"
              >
                {t('profile.done')}
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* MFA Disable Dialog */}
      <Dialog open={mfaDisableDialogOpen} onOpenChange={(open) => {
        setMfaDisableDialogOpen(open)
        if (!open) setMfaDisablePassword("")
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('profile.disableMfaTitle')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              {t('profile.disableMfaDescription')}
            </p>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('auth.password')}</label>
              <Input
                type="password"
                value={mfaDisablePassword}
                onChange={(e) => setMfaDisablePassword(e.target.value)}
              />
            </div>
            <Button
              onClick={handleDisableMfa}
              disabled={disableMfaMutation.isPending || !mfaDisablePassword}
              variant="destructive"
              className="w-full"
            >
              {disableMfaMutation.isPending ? t('profile.disabling') : t('profile.disableMfa')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
