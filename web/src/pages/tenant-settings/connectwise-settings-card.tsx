import { useState } from "react"
import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import {
  useCWConfig,
  useCreateCWConfig,
  useUpdateCWConfig,
  useDeleteCWConfig,
  useTestCWConfig,
  useCWCompanyMappings,
  useAddCWCompanyMapping,
  useDeleteCWCompanyMapping,
  useCWBoards,
  useCWBoardStatuses,
  useCWBoardTypes,
  useCWTicketLogs,
  useCWTicketLogStats,
} from "@/api/connectwise"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"
import { ConnectWiseConnectionTab } from "./connectwise-connection-tab"
import { ConnectWiseAutomationTab } from "./connectwise-automation-tab"
import { ConnectWiseMappingsTab } from "./connectwise-mappings-tab"
import { ConnectWiseActivityTab } from "./connectwise-activity-tab"

// Connection form schema
const connectionSchema = z.object({
  company_id: z.string().min(1, "Company ID is required"),
  public_key: z.string().optional(),
  private_key: z.string().optional(),
  client_id: z.string().min(1, "Client ID is required"),
  base_url: z.string().url("Must be a valid URL").default("https://na.myconnectwise.net"),
})

export type ConnectionFormValues = z.infer<typeof connectionSchema>

// Automation form schema
const automationSchema = z.object({
  auto_ticket_missed_calls: z.boolean().default(true),
  auto_ticket_voicemails: z.boolean().default(true),
  auto_ticket_completed_calls: z.boolean().default(false),
  min_call_duration_seconds: z.coerce.number().int().min(0).default(0),
  default_board_id: z.coerce.number().int().nullable().optional(),
  default_status_id: z.coerce.number().int().nullable().optional(),
  default_type_id: z.coerce.number().int().nullable().optional(),
})

export type AutomationFormValues = z.infer<typeof automationSchema>

export function ConnectWiseSettingsCard() {
  const { t } = useTranslation()
  const { data: config, isLoading, error: configError } = useCWConfig()
  const createMutation = useCreateCWConfig()
  const updateMutation = useUpdateCWConfig()
  const deleteMutation = useDeleteCWConfig()
  const testMutation = useTestCWConfig()
  const { data: mappings } = useCWCompanyMappings()
  const addMappingMutation = useAddCWCompanyMapping()
  const deleteMappingMutation = useDeleteCWCompanyMapping()
  const { data: boards } = useCWBoards()
  const { data: ticketLogs } = useCWTicketLogs()
  const { data: stats } = useCWTicketLogStats()

  const [showSetup, setShowSetup] = useState(false)

  const isConfigured = !!config && !configError

  // Board-dependent queries
  const selectedBoardId = config?.default_board_id ?? null
  const { data: boardStatuses } = useCWBoardStatuses(selectedBoardId)
  const { data: boardTypes } = useCWBoardTypes(selectedBoardId)

  // Connection form
  const connectionForm = useForm<ConnectionFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(connectionSchema) as any,
    defaultValues: {
      company_id: "",
      public_key: "",
      private_key: "",
      client_id: "",
      base_url: "https://na.myconnectwise.net",
    },
    values: isConfigured
      ? {
          company_id: config.company_id,
          public_key: "",
          private_key: "",
          client_id: config.client_id,
          base_url: config.base_url,
        }
      : undefined,
  })

  // Automation form
  const automationForm = useForm<AutomationFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(automationSchema) as any,
    values: isConfigured
      ? {
          auto_ticket_missed_calls: config.auto_ticket_missed_calls,
          auto_ticket_voicemails: config.auto_ticket_voicemails,
          auto_ticket_completed_calls: config.auto_ticket_completed_calls,
          min_call_duration_seconds: config.min_call_duration_seconds,
          default_board_id: config.default_board_id,
          default_status_id: config.default_status_id,
          default_type_id: config.default_type_id,
        }
      : undefined,
  })

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const onConnectionSubmit = async (data: ConnectionFormValues) => {
    try {
      if (isConfigured) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const updateData: Record<string, any> = { ...data }
        if (!updateData.public_key) delete updateData.public_key
        if (!updateData.private_key) delete updateData.private_key
        await updateMutation.mutateAsync(updateData)
        toast.success(t("connectwise.configUpdated"))
      } else {
        if (!data.public_key || !data.private_key) {
          toast.error(t("connectwise.keysRequired"))
          return
        }
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        await createMutation.mutateAsync(data as any)
        toast.success(t("connectwise.configCreated"))
        setShowSetup(false)
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      toast.error(err?.detail || err?.message || t("connectwise.saveFailed"))
    }
  }

  const onAutomationSubmit = async (data: AutomationFormValues) => {
    try {
      await updateMutation.mutateAsync(data)
      toast.success(t("connectwise.automationUpdated"))
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      toast.error(err?.detail || err?.message || t("connectwise.saveFailed"))
    }
  }

  const handleTest = async () => {
    try {
      const result = await testMutation.mutateAsync()
      if (result.success) {
        toast.success(t("connectwise.testSuccess"))
      } else {
        toast.error(result.message)
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      toast.error(err?.detail || err?.message || t("connectwise.testFailed"))
    }
  }

  const handleDelete = async () => {
    if (!confirm(t("connectwise.deleteConfirm"))) return
    try {
      await deleteMutation.mutateAsync()
      toast.success(t("connectwise.configDeleted"))
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      toast.error(err?.detail || err?.message || t("connectwise.deleteFailed"))
    }
  }

  const handleAddMapping = async (data: {
    cw_company_id: number
    cw_company_name: string
    extension_id: string | null
    did_id: string | null
  }) => {
    try {
      await addMappingMutation.mutateAsync(data)
      toast.success(t("connectwise.mappingAdded"))
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      toast.error(err?.detail || err?.message || t("connectwise.mappingFailed"))
    }
  }

  const handleDeleteMapping = async (mappingId: string) => {
    try {
      await deleteMappingMutation.mutateAsync(mappingId)
      toast.success(t("connectwise.mappingDeleted"))
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      toast.error(err?.detail || err?.message || t("connectwise.mappingDeleteFailed"))
    }
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("connectwise.title")}</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-32" />
        </CardContent>
      </Card>
    )
  }

  if (!isConfigured && !showSetup) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("connectwise.title")}</CardTitle>
          <CardDescription>{t("connectwise.notConfigured")}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={() => setShowSetup(true)}>{t("connectwise.setupButton")}</Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("connectwise.title")}</CardTitle>
        <CardDescription>
          {isConfigured ? t("connectwise.configuredDescription") : t("connectwise.setupDescription")}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="connection">
          <TabsList>
            <TabsTrigger value="connection">{t("connectwise.connectionTab")}</TabsTrigger>
            {isConfigured && (
              <>
                <TabsTrigger value="automation">{t("connectwise.automationTab")}</TabsTrigger>
                <TabsTrigger value="mappings">{t("connectwise.mappingsTab")}</TabsTrigger>
                <TabsTrigger value="activity">{t("connectwise.activityTab")}</TabsTrigger>
              </>
            )}
          </TabsList>

          <ConnectWiseConnectionTab
            connectionForm={connectionForm}
            isConfigured={isConfigured}
            isSaving={createMutation.isPending || updateMutation.isPending}
            onSubmit={onConnectionSubmit}
            onTest={handleTest}
            isTesting={testMutation.isPending}
            onDelete={handleDelete}
            isDeleting={deleteMutation.isPending}
            onCancel={() => setShowSetup(false)}
          />

          {isConfigured && (
            <ConnectWiseAutomationTab
              automationForm={automationForm}
              boards={boards}
              boardStatuses={boardStatuses}
              boardTypes={boardTypes}
              selectedBoardId={selectedBoardId}
              isSaving={updateMutation.isPending}
              onSubmit={onAutomationSubmit}
            />
          )}

          {isConfigured && (
            <ConnectWiseMappingsTab
              mappings={mappings}
              onAddMapping={handleAddMapping}
              isAddingMapping={addMappingMutation.isPending}
              onDeleteMapping={handleDeleteMapping}
              isDeletingMapping={deleteMappingMutation.isPending}
            />
          )}

          {isConfigured && (
            <ConnectWiseActivityTab
              ticketLogs={ticketLogs}
              stats={stats}
            />
          )}
        </Tabs>
      </CardContent>
    </Card>
  )
}
