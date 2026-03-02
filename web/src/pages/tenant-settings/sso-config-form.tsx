import { useTranslation } from "react-i18next"
import { type UseFormReturn } from "react-hook-form"
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { type SSOConfigFormValues, ROLES } from "./sso-settings-card"

interface SSOConfigFormProps {
  form: UseFormReturn<SSOConfigFormValues>
  isConfigured: boolean
  isSaving: boolean
  onSubmit: (data: SSOConfigFormValues) => Promise<void>
  onTest: () => Promise<void>
  isTesting: boolean
  onDelete: () => Promise<void>
  isDeleting: boolean
  onCancel: () => void
}

export function SSOConfigForm({
  form,
  isConfigured,
  isSaving,
  onSubmit,
  onTest,
  isTesting,
  onDelete,
  isDeleting,
  onCancel,
}: SSOConfigFormProps) {
  const { t } = useTranslation()
  const watchProviderType = form.watch("provider_type")

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4 max-w-lg">
        <FormField
          control={form.control}
          name="provider_type"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("sso.providerType")}</FormLabel>
              <FormControl>
                <Select
                  value={field.value}
                  onValueChange={(v) => {
                    field.onChange(v)
                    if (v === "microsoft" && !form.getValues("issuer_url")) {
                      form.setValue("issuer_url", "https://login.microsoftonline.com/{tenant-id}/v2.0")
                    } else if (v === "google" && !form.getValues("issuer_url")) {
                      form.setValue("issuer_url", "https://accounts.google.com")
                    }
                  }}
                  disabled={isConfigured}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="microsoft">{t("sso.providerMicrosoft")}</SelectItem>
                    <SelectItem value="google">{t("sso.providerGoogle")}</SelectItem>
                  </SelectContent>
                </Select>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="display_name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("sso.displayName")}</FormLabel>
              <FormControl>
                <Input {...field} placeholder={watchProviderType === "microsoft" ? "Microsoft Entra ID" : "Google Workspace"} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="client_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("sso.clientId")}</FormLabel>
              <FormControl>
                <Input {...field} placeholder={t("sso.clientIdPlaceholder")} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="client_secret"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("sso.clientSecret")}</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  type="password"
                  placeholder={isConfigured ? t("sso.clientSecretUnchanged") : t("sso.clientSecretPlaceholder")}
                />
              </FormControl>
              <FormDescription>
                {isConfigured ? t("sso.clientSecretUpdateHint") : ""}
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="issuer_url"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("sso.issuerUrl")}</FormLabel>
              <FormControl>
                <Input {...field} placeholder="https://login.microsoftonline.com/{tenant-id}/v2.0" />
              </FormControl>
              <FormDescription>{t("sso.issuerUrlHint")}</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="scopes"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("sso.scopes")}</FormLabel>
              <FormControl>
                <Input {...field} placeholder="openid email profile" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="auto_provision"
          render={({ field }) => (
            <FormItem className="flex items-center justify-between rounded-lg border p-3">
              <div className="space-y-0.5">
                <FormLabel>{t("sso.autoProvision")}</FormLabel>
                <FormDescription>{t("sso.autoProvisionDescription")}</FormDescription>
              </div>
              <FormControl>
                <Switch checked={field.value} onCheckedChange={field.onChange} />
              </FormControl>
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="default_role"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("sso.defaultRole")}</FormLabel>
              <FormControl>
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ROLES.map((role) => (
                      <SelectItem key={role.value} value={role.value}>
                        {role.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormControl>
              <FormDescription>{t("sso.defaultRoleDescription")}</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="enforce_sso"
          render={({ field }) => (
            <FormItem className="flex items-center justify-between rounded-lg border p-3">
              <div className="space-y-0.5">
                <FormLabel>{t("sso.enforceSso")}</FormLabel>
                <FormDescription>{t("sso.enforceSsoDescription")}</FormDescription>
              </div>
              <FormControl>
                <Switch checked={field.value} onCheckedChange={field.onChange} />
              </FormControl>
            </FormItem>
          )}
        />

        <div className="flex gap-2">
          <Button type="submit" disabled={isSaving}>
            {isSaving ? t("common.saving") : t("common.save")}
          </Button>
          {isConfigured && (
            <>
              <Button type="button" variant="outline" onClick={onTest} disabled={isTesting}>
                {isTesting ? t("sso.testing") : t("sso.testConnection")}
              </Button>
              <Button type="button" variant="destructive" onClick={onDelete} disabled={isDeleting}>
                {t("common.delete")}
              </Button>
            </>
          )}
          {!isConfigured && (
            <Button type="button" variant="outline" onClick={onCancel}>
              {t("common.cancel")}
            </Button>
          )}
        </div>
      </form>
    </Form>
  )
}
