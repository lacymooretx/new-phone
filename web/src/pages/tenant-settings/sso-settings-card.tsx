import { useState } from "react"
import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import {
  useSSOConfig,
  useCreateSSOConfig,
  useUpdateSSOConfig,
  useDeleteSSOConfig,
  useTestSSOConfig,
  useSSORoleMappings,
  useAddRoleMapping,
  useDeleteRoleMapping,
} from "@/api/sso"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"
import { SSOConfigForm } from "./sso-config-form"
import { SSORoleMappings } from "./sso-role-mappings"

const ssoConfigSchema = z.object({
  provider_type: z.enum(["microsoft", "google"]),
  display_name: z.string().min(1, "Display name is required"),
  client_id: z.string().min(1, "Client ID is required"),
  client_secret: z.string().optional(),
  issuer_url: z.string().url("Must be a valid URL"),
  scopes: z.string().default("openid email profile"),
  auto_provision: z.boolean().default(true),
  default_role: z.string().default("tenant_user"),
  enforce_sso: z.boolean().default(false),
})

export type SSOConfigFormValues = z.infer<typeof ssoConfigSchema>

export const ROLES = [
  { value: "tenant_admin", label: "Tenant Admin" },
  { value: "tenant_manager", label: "Tenant Manager" },
  { value: "tenant_user", label: "Tenant User" },
]

export function SSOSettingsCard() {
  const { t } = useTranslation()
  const { data: config, isLoading, error: configError } = useSSOConfig()
  const createMutation = useCreateSSOConfig()
  const updateMutation = useUpdateSSOConfig()
  const deleteMutation = useDeleteSSOConfig()
  const testMutation = useTestSSOConfig()
  const { data: roleMappings } = useSSORoleMappings()
  const addMappingMutation = useAddRoleMapping()
  const deleteMappingMutation = useDeleteRoleMapping()

  const [showSetup, setShowSetup] = useState(false)

  const isConfigured = !!config && !configError

  const form = useForm<SSOConfigFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(ssoConfigSchema) as any,
    defaultValues: {
      provider_type: "microsoft",
      display_name: "",
      client_id: "",
      client_secret: "",
      issuer_url: "",
      scopes: "openid email profile",
      auto_provision: true,
      default_role: "tenant_user",
      enforce_sso: false,
    },
    values: isConfigured
      ? {
          provider_type: config.provider_type,
          display_name: config.display_name,
          client_id: config.client_id,
          client_secret: "",
          issuer_url: config.issuer_url,
          scopes: config.scopes,
          auto_provision: config.auto_provision,
          default_role: config.default_role,
          enforce_sso: config.enforce_sso,
        }
      : undefined,
  })

  const onSubmit = async (data: SSOConfigFormValues) => {
    try {
      if (isConfigured) {
        const updateData: Record<string, any> = { ...data }
        if (!updateData.client_secret) delete updateData.client_secret
        await updateMutation.mutateAsync(updateData)
        toast.success(t("sso.configUpdated"))
      } else {
        if (!data.client_secret) {
          toast.error(t("sso.clientSecretRequired"))
          return
        }
        await createMutation.mutateAsync(data as any)
        toast.success(t("sso.configCreated"))
        setShowSetup(false)
      }
    } catch (err: any) {
      toast.error(err?.detail || err?.message || t("sso.saveFailed"))
    }
  }

  const handleTest = async () => {
    try {
      const result = await testMutation.mutateAsync()
      if (result.success) {
        toast.success(t("sso.testSuccess"))
      } else {
        toast.error(result.message)
      }
    } catch (err: any) {
      toast.error(err?.detail || err?.message || t("sso.testFailed"))
    }
  }

  const handleDelete = async () => {
    if (!confirm(t("sso.deleteConfirm"))) return
    try {
      await deleteMutation.mutateAsync()
      toast.success(t("sso.configDeleted"))
    } catch (err: any) {
      toast.error(err?.detail || err?.message || t("sso.deleteFailed"))
    }
  }

  const handleAddMapping = async (data: { external_group_id: string; external_group_name?: string; pbx_role: string }) => {
    try {
      await addMappingMutation.mutateAsync(data)
      toast.success(t("sso.mappingAdded"))
    } catch (err: any) {
      toast.error(err?.detail || err?.message || t("sso.mappingFailed"))
    }
  }

  const handleDeleteMapping = async (mappingId: string) => {
    try {
      await deleteMappingMutation.mutateAsync(mappingId)
      toast.success(t("sso.mappingDeleted"))
    } catch (err: any) {
      toast.error(err?.detail || err?.message || t("sso.mappingDeleteFailed"))
    }
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("sso.title")}</CardTitle>
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
          <CardTitle>{t("sso.title")}</CardTitle>
          <CardDescription>{t("sso.notConfigured")}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={() => setShowSetup(true)}>{t("sso.setupButton")}</Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("sso.title")}</CardTitle>
        <CardDescription>
          {isConfigured ? t("sso.configuredDescription") : t("sso.setupDescription")}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <SSOConfigForm
          form={form}
          isConfigured={isConfigured}
          isSaving={createMutation.isPending || updateMutation.isPending}
          onSubmit={onSubmit}
          onTest={handleTest}
          isTesting={testMutation.isPending}
          onDelete={handleDelete}
          isDeleting={deleteMutation.isPending}
          onCancel={() => setShowSetup(false)}
        />

        {isConfigured && (
          <SSORoleMappings
            roleMappings={roleMappings}
            onAddMapping={handleAddMapping}
            isAddingMapping={addMappingMutation.isPending}
            onDeleteMapping={handleDeleteMapping}
            isDeletingMapping={deleteMappingMutation.isPending}
          />
        )}
      </CardContent>
    </Card>
  )
}
