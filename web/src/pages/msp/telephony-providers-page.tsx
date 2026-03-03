import { useState } from "react"
import { useTranslation } from "react-i18next"
import i18next from "i18next"
import {
  usePlatformTelephonyProviders,
  useCreatePlatformTelephonyProvider,
  useUpdatePlatformTelephonyProvider,
  useDeletePlatformTelephonyProvider,
  type TelephonyProviderConfig,
  type TelephonyProviderConfigCreate,
} from "@/api/telephony-providers"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { EmptyState } from "@/components/shared/empty-state"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Plus, Server, MoreHorizontal, Pencil, Trash2 } from "lucide-react"
import { toast } from "sonner"
import type { ColumnDef } from "@tanstack/react-table"
import { TelephonyProviderDialog } from "./telephony-provider-dialog"

function getColumns(actions: {
  onEdit: (c: TelephonyProviderConfig) => void
  onDelete: (c: TelephonyProviderConfig) => void
}): ColumnDef<TelephonyProviderConfig>[] {
  return [
    {
      accessorKey: "provider_type",
      header: i18next.t("telephonyProviders.col.provider"),
      cell: ({ row }) => (
        <span className="capitalize font-medium">{row.original.provider_type}</span>
      ),
    },
    {
      accessorKey: "label",
      header: i18next.t("telephonyProviders.col.label"),
    },
    {
      accessorKey: "is_default",
      header: i18next.t("telephonyProviders.col.default"),
      cell: ({ row }) =>
        row.original.is_default ? (
          <Badge variant="default" className="text-xs">
            {i18next.t("telephonyProviders.col.default")}
          </Badge>
        ) : null,
    },
    {
      accessorKey: "is_active",
      header: i18next.t("telephonyProviders.col.status"),
      cell: ({ row }) => (
        <Badge variant={row.original.is_active ? "outline" : "secondary"}>
          {row.original.is_active
            ? i18next.t("common.active")
            : i18next.t("common.inactive")}
        </Badge>
      ),
    },
    {
      accessorKey: "created_at",
      header: i18next.t("telephonyProviders.col.created"),
      cell: ({ row }) =>
        new Date(row.original.created_at).toLocaleDateString(),
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => actions.onEdit(row.original)}>
              <Pencil className="mr-2 h-4 w-4" /> {i18next.t("common.edit")}
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => actions.onDelete(row.original)}
              className="text-destructive"
            >
              <Trash2 className="mr-2 h-4 w-4" /> {i18next.t("common.delete")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]
}

export function TelephonyProvidersPage() {
  const { t } = useTranslation()
  const { data: providers, isLoading, isError, error } = usePlatformTelephonyProviders()
  const createMutation = useCreatePlatformTelephonyProvider()
  const updateMutation = useUpdatePlatformTelephonyProvider()
  const deleteMutation = useDeletePlatformTelephonyProvider()

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

  const columns = getColumns({
    onEdit: (c) => {
      setEditing(c)
      setDialogOpen(true)
    },
    onDelete: (c) => {
      setDeleting(c)
      setConfirmOpen(true)
    },
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("telephonyProviders.title")}
        description={t("telephonyProviders.description")}
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "MSP" },
          { label: t("telephonyProviders.title") },
        ]}
      >
        <Button
          onClick={() => {
            setEditing(null)
            setDialogOpen(true)
          }}
        >
          <Plus className="mr-2 h-4 w-4" /> {t("telephonyProviders.create")}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t("common.failedToLoad", {
            message: error?.message || t("common.unknownError"),
          })}
        </div>
      )}

      <DataTable
        columns={columns}
        data={providers ?? []}
        isLoading={isLoading}
        searchPlaceholder={t("telephonyProviders.searchPlaceholder")}
        emptyState={
          <EmptyState
            icon={Server}
            title={t("telephonyProviders.emptyTitle")}
            description={t("telephonyProviders.emptyDescription")}
            actionLabel={t("telephonyProviders.create")}
            onAction={() => {
              setEditing(null)
              setDialogOpen(true)
            }}
          />
        }
      />

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
    </div>
  )
}
