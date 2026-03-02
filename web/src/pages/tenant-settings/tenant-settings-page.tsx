import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { useTenant, useUpdateTenant } from "@/api/tenants"
import { SSOSettingsCard } from "./sso-settings-card"
import { ConnectWiseSettingsCard } from "./connectwise-settings-card"
import { useAuthStore } from "@/stores/auth-store"
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
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"

const settingsSchema = z.object({
  name: z.string().min(1, "Organization name is required"),
  domain: z.string().nullable().optional(),
  sip_domain: z.string().nullable().optional(),
  notes: z.string().nullable().optional(),
  default_language: z.string().default("en"),
})

type SettingsFormValues = z.infer<typeof settingsSchema>

export function TenantSettingsPage() {
  const { t } = useTranslation()
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const { data: tenant, isLoading } = useTenant(tenantId)
  const updateMutation = useUpdateTenant()

  const form = useForm<SettingsFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(settingsSchema) as any,
    defaultValues: {
      name: "",
      domain: "",
      sip_domain: "",
      notes: "",
      default_language: "en",
    },
  })

  useEffect(() => {
    if (tenant) {
      form.reset({
        name: tenant.name,
        domain: tenant.domain ?? "",
        sip_domain: tenant.sip_domain ?? "",
        notes: tenant.notes ?? "",
        default_language: (tenant as any).default_language ?? "en",
      })
    }
  }, [tenant, form])

  const onSubmit = (data: SettingsFormValues) => {
    updateMutation.mutate(
      {
        id: tenantId,
        name: data.name,
        domain: data.domain || null,
        sip_domain: data.sip_domain || null,
        notes: data.notes || null,
        default_language: data.default_language,
      } as any,
      {
        onSuccess: () => toast.success(t('tenantSettings.settingsSaved')),
        onError: (err) => toast.error(err.message),
      }
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('tenantSettings.title')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Settings" }]} />
        <Skeleton className="h-64" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader title={t('tenantSettings.title')} description={t('tenantSettings.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Settings" }]} />

      <Card>
        <CardHeader>
          <CardTitle>{t('tenantSettings.general')}</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4 max-w-lg">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('tenantSettings.organizationName')}</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="domain"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('tenantSettings.domain')}</FormLabel>
                    <FormControl>
                      <Input {...field} value={field.value ?? ""} placeholder={t('tenantSettings.domainPlaceholder')} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="sip_domain"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('tenantSettings.sipDomain')}</FormLabel>
                    <FormControl>
                      <Input {...field} value={field.value ?? ""} placeholder={t('tenantSettings.sipDomainPlaceholder')} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="notes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('tenantSettings.notes')}</FormLabel>
                    <FormControl>
                      <Textarea {...field} value={field.value ?? ""} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="default_language"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('tenantSettings.defaultLanguage')}</FormLabel>
                    <FormControl>
                      <Select value={field.value || "en"} onValueChange={field.onChange}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="en">{t('languages.en')}</SelectItem>
                          <SelectItem value="es">{t('languages.es')}</SelectItem>
                          <SelectItem value="fr">{t('languages.fr')}</SelectItem>
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <p className="text-xs text-muted-foreground">{t('tenantSettings.defaultLanguageDescription')}</p>
                  </FormItem>
                )}
              />
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? t('common.saving') : t('tenantSettings.saveChanges')}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>

      <SSOSettingsCard />

      <ConnectWiseSettingsCard />
    </div>
  )
}
