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
import { TabsContent } from "@/components/ui/tabs"
import { type ConnectionFormValues } from "./connectwise-settings-card"

interface ConnectWiseConnectionTabProps {
  connectionForm: UseFormReturn<ConnectionFormValues>
  isConfigured: boolean
  isSaving: boolean
  onSubmit: (data: ConnectionFormValues) => Promise<void>
  onTest: () => Promise<void>
  isTesting: boolean
  onDelete: () => Promise<void>
  isDeleting: boolean
  onCancel: () => void
}

export function ConnectWiseConnectionTab({
  connectionForm,
  isConfigured,
  isSaving,
  onSubmit,
  onTest,
  isTesting,
  onDelete,
  isDeleting,
  onCancel,
}: ConnectWiseConnectionTabProps) {
  const { t } = useTranslation()

  return (
    <TabsContent value="connection" className="space-y-4">
      <Form {...connectionForm}>
        <form onSubmit={connectionForm.handleSubmit(onSubmit)} className="space-y-4 max-w-lg">
          <FormField
            control={connectionForm.control}
            name="company_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("connectwise.companyId")}</FormLabel>
                <FormControl>
                  <Input {...field} placeholder={t("connectwise.companyIdPlaceholder")} />
                </FormControl>
                <FormDescription>{t("connectwise.companyIdHint")}</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={connectionForm.control}
            name="public_key"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("connectwise.publicKey")}</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    type="password"
                    placeholder={isConfigured ? t("connectwise.keyUnchanged") : t("connectwise.publicKeyPlaceholder")}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={connectionForm.control}
            name="private_key"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("connectwise.privateKey")}</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    type="password"
                    placeholder={isConfigured ? t("connectwise.keyUnchanged") : t("connectwise.privateKeyPlaceholder")}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={connectionForm.control}
            name="client_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("connectwise.clientId")}</FormLabel>
                <FormControl>
                  <Input {...field} placeholder={t("connectwise.clientIdPlaceholder")} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={connectionForm.control}
            name="base_url"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("connectwise.baseUrl")}</FormLabel>
                <FormControl>
                  <Input {...field} placeholder="https://na.myconnectwise.net" />
                </FormControl>
                <FormDescription>{t("connectwise.baseUrlHint")}</FormDescription>
                <FormMessage />
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
                  {isTesting ? t("connectwise.testing") : t("connectwise.testConnection")}
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
    </TabsContent>
  )
}
