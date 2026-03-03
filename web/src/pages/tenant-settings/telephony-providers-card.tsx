import { useState } from "react"
import { useTranslation } from "react-i18next"
import {
  useTenantTelephonyProviders,
  useTenantEffectiveProviders,
  useCreateTenantTelephonyProvider,
  useUpdateTenantTelephonyProvider,
  useDeleteTenantTelephonyProvider,
  type TelephonyProviderConfig,
  type TelephonyProviderConfigCreate,
} from "@/api/telephony-providers"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { TelephonyProviderDialog } from "@/pages/msp/telephony-provider-dialog"
import { Plus, Pencil, Trash2, Server } from "lucide-react"
import { toast } from "sonner"

function SourceBadge({ source }: { source: string }) {
  const { t } = useTranslation()
  const variants: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
    tenant: "default",
    msp: "secondary",
    env_var: "outline",
    none: "destructive",
  }
  return (
    <Badge variant={variants[source] ?? "outline"}>
      {t(`telephonyProviders.effective.${source}`)}
    </Badge>
  )
}

export function TelephonyProvidersCard() {
  const { t } = useTranslation()
  const { data: effective, isLoading: effectiveLoading } = useTenantEffectiveProviders()
  const { data: overrides } = useTenantTelephonyProviders()
  const createMutation = useCreateTenantTelephonyProvider()
  const updateMutation = useUpdateTenantTelephonyProvider()
  const deleteMutation = useDeleteTenantTelephonyProvider()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<TelephonyProviderConfig | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<TelephonyProviderConfig | null>(null)

  const handleSubmit = (payload: TelephonyProviderConfigCreate, id?: string) => {
    if (id) {
      updateMutation.mutate(
        { id, ...payload },
        {
          onSuccess: () => {
            setDialogOpen(false)
            setEditing(null)
            toast.success(t("toast.updated", { item: t("telephonyProviders.title") }))
          },
          onError: (err) => toast.error(err.message),
        },
      )
    } else {
      createMutation.mutate(payload, {
        onSuccess: () => {
          setDialogOpen(false)
          toast.success(t("toast.created", { item: t("telephonyProviders.title") }))
        },
        onError: (err) => toast.error(err.message),
      })
    }
  }

  const handleDelete = () => {
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => {
        setConfirmOpen(false)
        setDeleting(null)
        toast.success(t("telephonyProviders.deactivated"))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              {t("telephonyProviders.title")}
            </CardTitle>
            <CardDescription>{t("telephonyProviders.tenantDescription")}</CardDescription>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setEditing(null)
              setDialogOpen(true)
            }}
          >
            <Plus className="mr-2 h-4 w-4" /> {t("telephonyProviders.addOverride")}
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Effective provider status */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">
              {t("telephonyProviders.effective.title")}
            </h4>
            {effectiveLoading ? (
              <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
            ) : (
              <div className="grid gap-2">
                {effective?.map((ep) => (
                  <div
                    key={ep.provider_type}
                    className="flex items-center justify-between rounded-md border p-3"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-medium capitalize">{ep.provider_type}</span>
                      <SourceBadge source={ep.source} />
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {ep.label ?? (ep.is_configured ? t("telephonyProviders.effective.envConfigured") : t("telephonyProviders.effective.notConfigured"))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Tenant overrides */}
          {overrides && overrides.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-muted-foreground">
                {t("telephonyProviders.tenantOverrides")}
              </h4>
              <div className="grid gap-2">
                {overrides.map((cfg) => (
                  <div
                    key={cfg.id}
                    className="flex items-center justify-between rounded-md border p-3"
                  >
                    <div className="flex items-center gap-3">
                      <span className="capitalize">{cfg.provider_type}</span>
                      <span className="text-sm text-muted-foreground">{cfg.label}</span>
                      {cfg.is_default && (
                        <Badge variant="default" className="text-xs">
                          {t("telephonyProviders.col.default")}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => {
                          setEditing(cfg)
                          setDialogOpen(true)
                        }}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive"
                        onClick={() => {
                          setDeleting(cfg)
                          setConfirmOpen(true)
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <TelephonyProviderDialog
        open={dialogOpen}
        onOpenChange={(open) => {
          if (!open) setEditing(null)
          setDialogOpen(open)
        }}
        editing={editing}
        isLoading={createMutation.isPending || updateMutation.isPending}
        onSubmit={handleSubmit}
      />

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t("telephonyProviders.deactivateTitle")}
        description={t("telephonyProviders.deactivateConfirm", {
          name: deleting?.label,
        })}
        confirmLabel={t("telephonyProviders.deactivateButton")}
        variant="destructive"
        onConfirm={handleDelete}
      />
    </>
  )
}
