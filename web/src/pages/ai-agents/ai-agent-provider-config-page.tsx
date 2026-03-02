import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useForm } from "react-hook-form"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import {
  useAIProviderConfigs,
  useCreateAIProviderConfig,
  useUpdateAIProviderConfig,
  useDeleteAIProviderConfig,
  useTestAIProviderConfig,
  useAIAgentProviders,
  type AIProviderConfig,
} from "@/api/ai-agents"
import { PageHeader } from "@/components/shared/page-header"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Card,
  CardContent,
  CardDescription,
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Plus, Settings, CheckCircle, XCircle, CircleDashed, Trash2 } from "lucide-react"
import { toast } from "sonner"

const KNOWN_PROVIDERS = [
  { name: "openai", displayName: "OpenAI", description: "GPT-4o, Whisper, TTS, Realtime API" },
  { name: "deepgram", displayName: "Deepgram", description: "Speech-to-text, nova-2 models" },
  { name: "google_gemini", displayName: "Google Gemini", description: "Gemini models, multimodal AI" },
  { name: "elevenlabs", displayName: "ElevenLabs", description: "Text-to-speech, voice cloning" },
  { name: "anthropic", displayName: "Anthropic", description: "Claude models for LLM pipeline" },
]

const providerFormSchema = z.object({
  provider_name: z.string().min(1, "Required"),
  api_key: z.string().min(1, "Required"),
  base_url: z.string().optional().or(z.literal("")),
  model_id: z.string().optional().or(z.literal("")),
})

type ProviderFormValues = z.infer<typeof providerFormSchema>

function statusIcon(status: "connected" | "error" | "unconfigured") {
  switch (status) {
    case "connected":
      return <CheckCircle className="h-5 w-5 text-green-500" />
    case "error":
      return <XCircle className="h-5 w-5 text-destructive" />
    case "unconfigured":
      return <CircleDashed className="h-5 w-5 text-muted-foreground" />
  }
}

function statusBadgeVariant(status: "connected" | "error" | "unconfigured"): "default" | "destructive" | "secondary" {
  switch (status) {
    case "connected":
      return "default"
    case "error":
      return "destructive"
    case "unconfigured":
      return "secondary"
  }
}

export function AIAgentProviderConfigPage() {
  const { t } = useTranslation()
  const { data: configs, isLoading: configsLoading } = useAIProviderConfigs()
  const { data: providerStatuses } = useAIAgentProviders()
  const createMutation = useCreateAIProviderConfig()
  const updateMutation = useUpdateAIProviderConfig()
  const deleteMutation = useDeleteAIProviderConfig()
  const testMutation = useTestAIProviderConfig()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingConfig, setEditingConfig] = useState<AIProviderConfig | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<AIProviderConfig | null>(null)
  const [testingId, setTestingId] = useState<string | null>(null)

  const form = useForm<ProviderFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(providerFormSchema) as any,
    defaultValues: {
      provider_name: "",
      api_key: "",
      base_url: "",
      model_id: "",
    },
  })

  const openAddDialog = (providerName?: string) => {
    setEditingConfig(null)
    form.reset({
      provider_name: providerName ?? "",
      api_key: "",
      base_url: "",
      model_id: "",
    })
    setDialogOpen(true)
  }

  const openEditDialog = (config: AIProviderConfig) => {
    setEditingConfig(config)
    form.reset({
      provider_name: config.provider_name,
      api_key: "",
      base_url: config.base_url ?? "",
      model_id: config.model_id ?? "",
    })
    setDialogOpen(true)
  }

  const onSubmit = async (values: ProviderFormValues) => {
    try {
      if (editingConfig) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const updateData = {
          id: editingConfig.id,
          base_url: values.base_url || null,
          model_id: values.model_id || null,
          ...(values.api_key ? { api_key: values.api_key } : {}),
        }
        await updateMutation.mutateAsync(updateData)
        toast.success(t("aiAgents.providers.configUpdated"))
      } else {
        await createMutation.mutateAsync({
          provider_name: values.provider_name,
          api_key: values.api_key,
          base_url: values.base_url || null,
          model_id: values.model_id || null,
        })
        toast.success(t("aiAgents.providers.configCreated"))
      }
      setDialogOpen(false)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      toast.error(err?.detail || err?.message || t("aiAgents.providers.saveFailed"))
    }
  }

  const handleTest = async (configId: string) => {
    setTestingId(configId)
    try {
      const result = await testMutation.mutateAsync(configId)
      if (result.success) {
        toast.success(t("aiAgents.providers.testSuccess"))
      } else {
        toast.error(result.message)
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      toast.error(err?.detail || err?.message || t("aiAgents.providers.testFailed"))
    } finally {
      setTestingId(null)
    }
  }

  const handleDelete = (config: AIProviderConfig) => {
    setDeleting(config)
    setConfirmOpen(true)
  }

  const confirmDelete = () => {
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => {
        setConfirmOpen(false)
        setDeleting(null)
        toast.success(t("aiAgents.providers.configDeleted"))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleToggleActive = async (config: AIProviderConfig) => {
    try {
      await updateMutation.mutateAsync({ id: config.id, is_active: !config.is_active })
      toast.success(
        config.is_active
          ? t("aiAgents.providers.providerDisabled")
          : t("aiAgents.providers.providerEnabled")
      )
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      toast.error(err?.detail || err?.message || t("aiAgents.providers.saveFailed"))
    }
  }

  const getConfigForProvider = (providerName: string): AIProviderConfig | undefined => {
    return configs?.find((c) => c.provider_name === providerName)
  }

  const getStatusForProvider = (providerName: string) => {
    return providerStatuses?.find((p) => p.name === providerName)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("aiAgents.providers.title")}
        description={t("aiAgents.providers.description")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "AI Agents" }, { label: t("aiAgents.providers.title") }]}
      >
        <Button onClick={() => openAddDialog()}>
          <Plus className="mr-2 h-4 w-4" /> {t("aiAgents.providers.addProvider")}
        </Button>
      </PageHeader>

      {configsLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {KNOWN_PROVIDERS.map((provider) => {
            const config = getConfigForProvider(provider.name)
            const status = getStatusForProvider(provider.name)
            const isConfigured = !!config

            return (
              <Card key={provider.name}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Settings className="h-5 w-5 text-muted-foreground" />
                      <CardTitle className="text-base">{provider.displayName}</CardTitle>
                    </div>
                    {status && statusIcon(status.status)}
                  </div>
                  <CardDescription>{provider.description}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Badge variant={status ? statusBadgeVariant(status.status) : "secondary"}>
                      {status
                        ? t(`aiAgents.providers.status_${status.status}`)
                        : t("aiAgents.providers.status_unconfigured")}
                    </Badge>
                    {config && (
                      <div className="flex items-center gap-2 ml-auto">
                        <Switch
                          checked={config.is_active}
                          onCheckedChange={() => handleToggleActive(config)}
                        />
                      </div>
                    )}
                  </div>

                  {config?.model_id && (
                    <p className="text-xs text-muted-foreground">
                      {t("aiAgents.providers.model")}: {config.model_id}
                    </p>
                  )}

                  <div className="flex gap-2">
                    {isConfigured ? (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => openEditDialog(config)}
                        >
                          {t("common.edit")}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleTest(config.id)}
                          disabled={testingId === config.id}
                        >
                          {testingId === config.id
                            ? t("aiAgents.providers.testing")
                            : t("aiAgents.providers.testConnection")}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(config)}
                          className="text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </>
                    ) : (
                      <Button
                        variant="default"
                        size="sm"
                        onClick={() => openAddDialog(provider.name)}
                      >
                        {t("aiAgents.providers.configure")}
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}

          {/* Extra configured providers not in KNOWN_PROVIDERS */}
          {configs
            ?.filter((c) => !KNOWN_PROVIDERS.some((kp) => kp.name === c.provider_name))
            .map((config) => {
              const status = getStatusForProvider(config.provider_name)
              return (
                <Card key={config.id}>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Settings className="h-5 w-5 text-muted-foreground" />
                        <CardTitle className="text-base">{config.provider_name}</CardTitle>
                      </div>
                      {status && statusIcon(status.status)}
                    </div>
                    <CardDescription>{t("aiAgents.providers.customProvider")}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Badge variant={status ? statusBadgeVariant(status.status) : "secondary"}>
                        {status
                          ? t(`aiAgents.providers.status_${status.status}`)
                          : t("aiAgents.providers.status_unconfigured")}
                      </Badge>
                      <div className="flex items-center gap-2 ml-auto">
                        <Switch
                          checked={config.is_active}
                          onCheckedChange={() => handleToggleActive(config)}
                        />
                      </div>
                    </div>
                    {config.model_id && (
                      <p className="text-xs text-muted-foreground">
                        {t("aiAgents.providers.model")}: {config.model_id}
                      </p>
                    )}
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" onClick={() => openEditDialog(config)}>
                        {t("common.edit")}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTest(config.id)}
                        disabled={testingId === config.id}
                      >
                        {testingId === config.id
                          ? t("aiAgents.providers.testing")
                          : t("aiAgents.providers.testConnection")}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(config)}
                        className="text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
        </div>
      )}

      {/* Add/Edit Provider Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingConfig
                ? t("aiAgents.providers.editProvider")
                : t("aiAgents.providers.addProvider")}
            </DialogTitle>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="provider_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("aiAgents.providers.providerName")}</FormLabel>
                    <FormControl>
                      {editingConfig ? (
                        <Input {...field} disabled />
                      ) : (
                        <Select value={field.value} onValueChange={field.onChange}>
                          <SelectTrigger>
                            <SelectValue placeholder={t("aiAgents.providers.selectProvider")} />
                          </SelectTrigger>
                          <SelectContent>
                            {KNOWN_PROVIDERS.map((p) => (
                              <SelectItem key={p.name} value={p.name}>
                                {p.displayName}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="api_key"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("aiAgents.providers.apiKey")}</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        type="password"
                        placeholder={
                          editingConfig
                            ? t("aiAgents.providers.apiKeyUnchanged")
                            : t("aiAgents.providers.apiKeyPlaceholder")
                        }
                      />
                    </FormControl>
                    <FormDescription>{t("aiAgents.providers.apiKeyHint")}</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="model_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("aiAgents.providers.modelId")}</FormLabel>
                    <FormControl>
                      <Input {...field} placeholder={t("aiAgents.providers.modelIdPlaceholder")} />
                    </FormControl>
                    <FormDescription>{t("aiAgents.providers.modelIdHint")}</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="base_url"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("aiAgents.providers.baseUrl")}</FormLabel>
                    <FormControl>
                      <Input {...field} placeholder={t("aiAgents.providers.baseUrlPlaceholder")} />
                    </FormControl>
                    <FormDescription>{t("aiAgents.providers.baseUrlHint")}</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="flex gap-2 pt-2">
                <Button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending}
                >
                  {(createMutation.isPending || updateMutation.isPending)
                    ? t("common.saving")
                    : t("common.save")}
                </Button>
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                  {t("common.cancel")}
                </Button>
              </div>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t("aiAgents.providers.deleteTitle")}
        description={t("aiAgents.providers.deleteConfirm", { name: deleting?.provider_name })}
        confirmLabel={t("common.delete")}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
