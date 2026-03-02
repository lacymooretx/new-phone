import { useTranslation } from "react-i18next"
import { type UseFormReturn } from "react-hook-form"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Switch } from "@/components/ui/switch"
import { type AIAgentContextFormValues } from "./ai-agent-context-form-page"

interface AIAgentBasicInfoCardProps {
  form: UseFormReturn<AIAgentContextFormValues>
  isEditing: boolean
}

export function AIAgentBasicInfoCard({ form, isEditing }: AIAgentBasicInfoCardProps) {
  const { t } = useTranslation()

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("aiAgents.contexts.basicInfo")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("aiAgents.contexts.formName")} *</FormLabel>
                <FormControl>
                  <Input {...field} placeholder={t("aiAgents.contexts.formNamePlaceholder")} disabled={isEditing} />
                </FormControl>
                <FormDescription>{t("aiAgents.contexts.formNameHint")}</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="display_name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("aiAgents.contexts.formDisplayName")} *</FormLabel>
                <FormControl>
                  <Input {...field} placeholder={t("aiAgents.contexts.formDisplayNamePlaceholder")} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <FormField
          control={form.control}
          name="greeting"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("aiAgents.contexts.formGreeting")} *</FormLabel>
              <FormControl>
                <Textarea {...field} placeholder={t("aiAgents.contexts.formGreetingPlaceholder")} rows={2} />
              </FormControl>
              <FormDescription>{t("aiAgents.contexts.formGreetingHint")}</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        {isEditing && (
          <FormField
            control={form.control}
            name="is_active"
            render={({ field }) => (
              <FormItem className="flex items-center justify-between rounded-lg border p-3">
                <div className="space-y-0.5">
                  <FormLabel>{t("aiAgents.contexts.formActive")}</FormLabel>
                  <FormDescription>{t("aiAgents.contexts.formActiveHint")}</FormDescription>
                </div>
                <FormControl>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
              </FormItem>
            )}
          />
        )}
      </CardContent>
    </Card>
  )
}
