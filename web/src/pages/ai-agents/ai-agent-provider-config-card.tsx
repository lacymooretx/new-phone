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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { type AIAgentContextFormValues } from "./ai-agent-context-form-page"

const PROVIDER_MODE_OPTIONS = [
  { value: "monolithic", labelKey: "aiAgents.contexts.monolithic" },
  { value: "pipeline", labelKey: "aiAgents.contexts.pipeline" },
]

interface AIProvider {
  name: string
  display_name: string
}

interface AIAgentProviderConfigCardProps {
  form: UseFormReturn<AIAgentContextFormValues>
  providerMode: string
  monolithicProviders: AIProvider[]
  sttProviders: AIProvider[]
  llmProviders: AIProvider[]
  ttsProviders: AIProvider[]
}

export function AIAgentProviderConfigCard({
  form,
  providerMode,
  monolithicProviders,
  sttProviders,
  llmProviders,
  ttsProviders,
}: AIAgentProviderConfigCardProps) {
  const { t } = useTranslation()

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("aiAgents.contexts.providerConfig")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <FormField
          control={form.control}
          name="provider_mode"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("aiAgents.contexts.formProviderMode")}</FormLabel>
              <FormControl>
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PROVIDER_MODE_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {t(opt.labelKey)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormControl>
              <FormDescription>{t("aiAgents.contexts.formProviderModeHint")}</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {providerMode === "monolithic" ? (
          <FormField
            control={form.control}
            name="monolithic_provider"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("aiAgents.contexts.formMonolithicProvider")}</FormLabel>
                <FormControl>
                  <Select value={field.value ?? ""} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder={t("aiAgents.contexts.selectProvider")} />
                    </SelectTrigger>
                    <SelectContent>
                      {monolithicProviders.map((p) => (
                        <SelectItem key={p.name} value={p.name}>
                          {p.display_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <FormField
              control={form.control}
              name="pipeline_stt"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("aiAgents.contexts.formSTT")}</FormLabel>
                  <FormControl>
                    <Select value={field.value ?? ""} onValueChange={field.onChange}>
                      <SelectTrigger>
                        <SelectValue placeholder={t("aiAgents.contexts.selectProvider")} />
                      </SelectTrigger>
                      <SelectContent>
                        {sttProviders.map((p) => (
                          <SelectItem key={p.name} value={p.name}>
                            {p.display_name}
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
              name="pipeline_llm"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("aiAgents.contexts.formLLM")}</FormLabel>
                  <FormControl>
                    <Select value={field.value ?? ""} onValueChange={field.onChange}>
                      <SelectTrigger>
                        <SelectValue placeholder={t("aiAgents.contexts.selectProvider")} />
                      </SelectTrigger>
                      <SelectContent>
                        {llmProviders.map((p) => (
                          <SelectItem key={p.name} value={p.name}>
                            {p.display_name}
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
              name="pipeline_tts"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("aiAgents.contexts.formTTS")}</FormLabel>
                  <FormControl>
                    <Select value={field.value ?? ""} onValueChange={field.onChange}>
                      <SelectTrigger>
                        <SelectValue placeholder={t("aiAgents.contexts.selectProvider")} />
                      </SelectTrigger>
                      <SelectContent>
                        {ttsProviders.map((p) => (
                          <SelectItem key={p.name} value={p.name}>
                            {p.display_name}
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
        )}
      </CardContent>
    </Card>
  )
}
