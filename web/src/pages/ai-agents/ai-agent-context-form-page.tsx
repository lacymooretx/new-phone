import { useEffect } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate, useParams } from "react-router"
import { useForm } from "react-hook-form"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import {
  useAIAgentContext,
  useCreateAIAgentContext,
  useUpdateAIAgentContext,
  useAIAgentTools,
  useAIAgentProviders,
  type AIAgentContextCreate,
} from "@/api/ai-agents"
import { PageHeader } from "@/components/shared/page-header"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
} from "@/components/ui/form"
import { Textarea } from "@/components/ui/textarea"
import { ArrowLeft } from "lucide-react"
import { toast } from "sonner"
import { AIAgentBasicInfoCard } from "./ai-agent-basic-info-card"
import { AIAgentProviderConfigCard } from "./ai-agent-provider-config-card"
import { AIAgentBehaviorCard } from "./ai-agent-behavior-card"
import { AIAgentToolsCard } from "./ai-agent-tools-card"

const contextSchema = z.object({
  name: z.string().min(1, "Required").max(100),
  display_name: z.string().min(1, "Required").max(200),
  system_prompt: z.string().min(1, "Required"),
  greeting: z.string().min(1, "Required").max(1000),
  provider_mode: z.enum(["monolithic", "pipeline"]),
  monolithic_provider: z.string().optional().or(z.literal("")),
  pipeline_stt: z.string().optional().or(z.literal("")),
  pipeline_llm: z.string().optional().or(z.literal("")),
  pipeline_tts: z.string().optional().or(z.literal("")),
  voice_id: z.string().optional().or(z.literal("")),
  language: z.string().default("en-US"),
  barge_in_enabled: z.boolean().default(true),
  barge_in_sensitivity: z.string().default("medium"),
  silence_timeout_ms: z.coerce.number().int().min(500).max(30000).default(2000),
  max_call_duration_seconds: z.coerce.number().int().min(30).max(7200).default(600),
  available_tools: z.array(z.string()).default([]),
  is_active: z.boolean().default(true),
})

export type AIAgentContextFormValues = z.infer<typeof contextSchema>

export function AIAgentContextFormPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const isEditing = !!id && id !== "new"

  const { data: existingContext, isLoading: contextLoading } = useAIAgentContext(isEditing ? id : "")
  const { data: tools } = useAIAgentTools()
  const { data: providers } = useAIAgentProviders()
  const createMutation = useCreateAIAgentContext()
  const updateMutation = useUpdateAIAgentContext()

  const form = useForm<AIAgentContextFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(contextSchema) as any,
    defaultValues: {
      name: "",
      display_name: "",
      system_prompt: "",
      greeting: "",
      provider_mode: "monolithic",
      monolithic_provider: "",
      pipeline_stt: "",
      pipeline_llm: "",
      pipeline_tts: "",
      voice_id: "",
      language: "en-US",
      barge_in_enabled: true,
      barge_in_sensitivity: "medium",
      silence_timeout_ms: 2000,
      max_call_duration_seconds: 600,
      available_tools: [],
      is_active: true,
    },
  })

  useEffect(() => {
    if (existingContext) {
      form.reset({
        name: existingContext.name,
        display_name: existingContext.display_name,
        system_prompt: existingContext.system_prompt,
        greeting: existingContext.greeting,
        provider_mode: existingContext.provider_mode,
        monolithic_provider: existingContext.monolithic_provider ?? "",
        pipeline_stt: existingContext.pipeline_stt ?? "",
        pipeline_llm: existingContext.pipeline_llm ?? "",
        pipeline_tts: existingContext.pipeline_tts ?? "",
        voice_id: existingContext.voice_id ?? "",
        language: existingContext.language,
        barge_in_enabled: existingContext.barge_in_enabled,
        barge_in_sensitivity: existingContext.barge_in_sensitivity,
        silence_timeout_ms: existingContext.silence_timeout_ms,
        max_call_duration_seconds: existingContext.max_call_duration_seconds,
        available_tools: existingContext.available_tools ?? [],
        is_active: existingContext.is_active,
      })
    }
  }, [existingContext, form])

  const providerMode = form.watch("provider_mode")

  const onSubmit = async (values: AIAgentContextFormValues) => {
    const data: AIAgentContextCreate = {
      name: values.name,
      display_name: values.display_name,
      system_prompt: values.system_prompt,
      greeting: values.greeting,
      provider_mode: values.provider_mode,
      monolithic_provider: values.monolithic_provider || null,
      pipeline_stt: values.pipeline_stt || null,
      pipeline_llm: values.pipeline_llm || null,
      pipeline_tts: values.pipeline_tts || null,
      voice_id: values.voice_id || null,
      language: values.language,
      barge_in_enabled: values.barge_in_enabled,
      barge_in_sensitivity: values.barge_in_sensitivity,
      silence_timeout_ms: values.silence_timeout_ms,
      max_call_duration_seconds: values.max_call_duration_seconds,
      available_tools: values.available_tools.length > 0 ? values.available_tools : null,
    }

    try {
      if (isEditing) {
        await updateMutation.mutateAsync({ id, ...data, is_active: values.is_active })
        toast.success(t("toast.updated", { item: t("aiAgents.contexts.title") }))
      } else {
        await createMutation.mutateAsync(data)
        toast.success(t("toast.created", { item: t("aiAgents.contexts.title") }))
      }
      navigate("/ai-agents/contexts")
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      toast.error(err?.detail || err?.message || t("aiAgents.contexts.saveFailed"))
    }
  }

  if (isEditing && contextLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  const monolithicProviders = providers?.filter(
    (p) => ["openai_realtime", "google_gemini"].includes(p.name) || p.name.includes("realtime")
  ) ?? providers ?? []

  const sttProviders = providers?.filter(
    (p) => ["deepgram", "google_stt", "openai_whisper"].includes(p.name) || p.name.includes("stt")
  ) ?? providers ?? []

  const llmProviders = providers?.filter(
    (p) => ["openai", "anthropic", "google_gemini"].includes(p.name) || p.name.includes("llm")
  ) ?? providers ?? []

  const ttsProviders = providers?.filter(
    (p) => ["elevenlabs", "google_tts", "openai_tts"].includes(p.name) || p.name.includes("tts")
  ) ?? providers ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title={isEditing ? t("aiAgents.contexts.edit") : t("aiAgents.contexts.create")}
        description={isEditing ? t("aiAgents.contexts.editDescription") : t("aiAgents.contexts.createDescription")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "AI Agents" }, { label: isEditing ? t("aiAgents.contexts.edit") : t("aiAgents.contexts.create") }]}
      >
        <Button variant="outline" onClick={() => navigate("/ai-agents/contexts")}>
          <ArrowLeft className="mr-2 h-4 w-4" /> {t("aiAgents.contexts.backToList")}
        </Button>
      </PageHeader>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <AIAgentBasicInfoCard form={form} isEditing={isEditing} />

          {/* System Prompt */}
          <Card>
            <CardHeader>
              <CardTitle>{t("aiAgents.contexts.systemPrompt")}</CardTitle>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="system_prompt"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("aiAgents.contexts.formSystemPrompt")} *</FormLabel>
                    <FormControl>
                      <Textarea
                        {...field}
                        placeholder={t("aiAgents.contexts.formSystemPromptPlaceholder")}
                        rows={10}
                        className="font-mono text-sm"
                      />
                    </FormControl>
                    <FormDescription>{t("aiAgents.contexts.formSystemPromptHint")}</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <AIAgentProviderConfigCard
            form={form}
            providerMode={providerMode}
            monolithicProviders={monolithicProviders}
            sttProviders={sttProviders}
            llmProviders={llmProviders}
            ttsProviders={ttsProviders}
          />

          <AIAgentBehaviorCard form={form} />

          <AIAgentToolsCard form={form} tools={tools} />

          {/* Submit */}
          <div className="flex gap-3">
            <Button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {(createMutation.isPending || updateMutation.isPending)
                ? t("common.saving")
                : isEditing
                  ? t("aiAgents.contexts.updateButton")
                  : t("aiAgents.contexts.createButton")}
            </Button>
            <Button type="button" variant="outline" onClick={() => navigate("/ai-agents/contexts")}>
              {t("common.cancel")}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  )
}
