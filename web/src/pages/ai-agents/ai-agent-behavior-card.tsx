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
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { type AIAgentContextFormValues } from "./ai-agent-context-form-page"

const BARGE_IN_OPTIONS = [
  { value: "low", labelKey: "aiAgents.contexts.bargeInLow" },
  { value: "medium", labelKey: "aiAgents.contexts.bargeInMedium" },
  { value: "high", labelKey: "aiAgents.contexts.bargeInHigh" },
]

const LANGUAGE_OPTIONS = [
  { value: "en-US", label: "English (US)" },
  { value: "en-GB", label: "English (UK)" },
  { value: "es-ES", label: "Spanish (Spain)" },
  { value: "es-MX", label: "Spanish (Mexico)" },
  { value: "fr-FR", label: "French (France)" },
  { value: "de-DE", label: "German" },
  { value: "pt-BR", label: "Portuguese (Brazil)" },
  { value: "ja-JP", label: "Japanese" },
  { value: "zh-CN", label: "Chinese (Simplified)" },
]

interface AIAgentBehaviorCardProps {
  form: UseFormReturn<AIAgentContextFormValues>
}

export function AIAgentBehaviorCard({ form }: AIAgentBehaviorCardProps) {
  const { t } = useTranslation()

  return (
    <>
      {/* Voice & Language */}
      <Card>
        <CardHeader>
          <CardTitle>{t("aiAgents.contexts.voiceAndLanguage")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField
              control={form.control}
              name="voice_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("aiAgents.contexts.formVoiceId")}</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder={t("aiAgents.contexts.formVoiceIdPlaceholder")} />
                  </FormControl>
                  <FormDescription>{t("aiAgents.contexts.formVoiceIdHint")}</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="language"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("aiAgents.contexts.formLanguage")}</FormLabel>
                  <FormControl>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {LANGUAGE_OPTIONS.map((lang) => (
                          <SelectItem key={lang.value} value={lang.value}>
                            {lang.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        </CardContent>
      </Card>

      {/* Behavior */}
      <Card>
        <CardHeader>
          <CardTitle>{t("aiAgents.contexts.behavior")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <FormField
            control={form.control}
            name="barge_in_enabled"
            render={({ field }) => (
              <FormItem className="flex items-center justify-between rounded-lg border p-3">
                <div className="space-y-0.5">
                  <FormLabel>{t("aiAgents.contexts.formBargeIn")}</FormLabel>
                  <FormDescription>{t("aiAgents.contexts.formBargeInHint")}</FormDescription>
                </div>
                <FormControl>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
              </FormItem>
            )}
          />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <FormField
              control={form.control}
              name="barge_in_sensitivity"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("aiAgents.contexts.formBargeInSensitivity")}</FormLabel>
                  <FormControl>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {BARGE_IN_OPTIONS.map((opt) => (
                          <SelectItem key={opt.value} value={opt.value}>
                            {t(opt.labelKey)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="silence_timeout_ms"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("aiAgents.contexts.formSilenceTimeout")}</FormLabel>
                  <FormControl>
                    <Input {...field} type="number" min={500} max={30000} step={100} />
                  </FormControl>
                  <FormDescription>{t("aiAgents.contexts.formSilenceTimeoutHint")}</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="max_call_duration_seconds"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("aiAgents.contexts.formMaxDuration")}</FormLabel>
                  <FormControl>
                    <Input {...field} type="number" min={30} max={7200} />
                  </FormControl>
                  <FormDescription>{t("aiAgents.contexts.formMaxDurationHint")}</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        </CardContent>
      </Card>
    </>
  )
}
