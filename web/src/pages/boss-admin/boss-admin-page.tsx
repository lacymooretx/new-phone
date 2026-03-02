import { useState, useCallback } from "react"
import { useTranslation } from "react-i18next"
import {
  useBossAdminRelationships,
  useCreateBossAdminRelationship,
  useUpdateBossAdminRelationship,
  useDeleteBossAdminRelationship,
  FILTER_MODES,
  type BossAdminRelationship,
  type BossAdminCreate,
  type BossAdminUpdate,
} from "@/api/boss-admin"
import { useExtensions, type Extension } from "@/api/extensions"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import { Plus, UserCog, X } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"
import { type ColumnDef } from "@tanstack/react-table"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { DataTableRowActions } from "@/components/data-table/data-table-row-actions"

function getColumns(opts: {
  onEdit: (r: BossAdminRelationship) => void
  onDelete: (r: BossAdminRelationship) => void
  t: (key: string) => string
}): ColumnDef<BossAdminRelationship>[] {
  return [
    {
      accessorKey: "executive_extension_number",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={opts.t("bossAdmin.col.executive")} />
      ),
      cell: ({ row }) => row.original.executive_extension_number ?? "—",
    },
    {
      accessorKey: "assistant_extension_number",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={opts.t("bossAdmin.col.assistant")} />
      ),
      cell: ({ row }) => row.original.assistant_extension_number ?? "—",
    },
    {
      accessorKey: "filter_mode",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={opts.t("bossAdmin.col.filterMode")} />
      ),
      cell: ({ row }) => {
        const mode = FILTER_MODES.find((m) => m.value === row.original.filter_mode)
        return mode ? opts.t(mode.labelKey) : row.original.filter_mode
      },
    },
    {
      accessorKey: "overflow_ring_time",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={opts.t("bossAdmin.col.overflowRingTime")} />
      ),
      cell: ({ row }) => `${row.original.overflow_ring_time}s`,
    },
    {
      accessorKey: "dnd_override_enabled",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={opts.t("bossAdmin.col.dndOverride")} />
      ),
      cell: ({ row }) => (
        <Badge variant={row.original.dnd_override_enabled ? "default" : "secondary"}>
          {row.original.dnd_override_enabled ? "Yes" : "No"}
        </Badge>
      ),
    },
    {
      accessorKey: "vip_caller_ids",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={opts.t("bossAdmin.col.vipCount")} />
      ),
      cell: ({ row }) => row.original.vip_caller_ids.length,
    },
    {
      accessorKey: "is_active",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title={opts.t("bossAdmin.col.status")} />
      ),
      cell: ({ row }) => (
        <Badge variant={row.original.is_active ? "default" : "secondary"}>
          {row.original.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <DataTableRowActions
          row={row}
          onEdit={() => opts.onEdit(row.original)}
          onDelete={() => opts.onDelete(row.original)}
        />
      ),
    },
  ]
}

function BossAdminForm({
  relationship,
  extensions,
  onSubmit,
  isLoading,
}: {
  relationship: BossAdminRelationship | null
  extensions: Extension[]
  onSubmit: (data: BossAdminCreate | BossAdminUpdate) => void
  isLoading: boolean
}) {
  const { t } = useTranslation()
  const isEditing = !!relationship

  const [executiveExtensionId, setExecutiveExtensionId] = useState(
    relationship?.executive_extension_id ?? ""
  )
  const [assistantExtensionId, setAssistantExtensionId] = useState(
    relationship?.assistant_extension_id ?? ""
  )
  const [filterMode, setFilterMode] = useState(
    relationship?.filter_mode ?? "all_to_assistant"
  )
  const [overflowRingTime, setOverflowRingTime] = useState(
    relationship?.overflow_ring_time ?? 20
  )
  const [dndOverrideEnabled, setDndOverrideEnabled] = useState(
    relationship?.dnd_override_enabled ?? false
  )
  const [vipCallerIds, setVipCallerIds] = useState<string[]>(
    relationship?.vip_caller_ids ?? []
  )
  const [vipInput, setVipInput] = useState("")
  const [isActive, setIsActive] = useState(relationship?.is_active ?? true)

  const handleAddVip = useCallback(() => {
    const trimmed = vipInput.trim()
    if (trimmed && !vipCallerIds.includes(trimmed)) {
      setVipCallerIds((prev) => [...prev, trimmed])
      setVipInput("")
    }
  }, [vipInput, vipCallerIds])

  const handleRemoveVip = useCallback((id: string) => {
    setVipCallerIds((prev) => prev.filter((v) => v !== id))
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (isEditing) {
      const data: BossAdminUpdate = {
        filter_mode: filterMode,
        overflow_ring_time: overflowRingTime,
        dnd_override_enabled: dndOverrideEnabled,
        vip_caller_ids: vipCallerIds,
        is_active: isActive,
      }
      onSubmit(data)
    } else {
      const data: BossAdminCreate = {
        executive_extension_id: executiveExtensionId,
        assistant_extension_id: assistantExtensionId,
        filter_mode: filterMode,
        overflow_ring_time: overflowRingTime,
        dnd_override_enabled: dndOverrideEnabled,
        vip_caller_ids: vipCallerIds,
      }
      onSubmit(data)
    }
  }

  const availableAssistants = extensions.filter(
    (ext) => ext.id !== executiveExtensionId
  )

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {!isEditing && (
        <>
          <div className="space-y-2">
            <Label>{t("bossAdmin.form.executiveExtension")}</Label>
            <Select
              value={executiveExtensionId}
              onValueChange={setExecutiveExtensionId}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {extensions.map((ext) => (
                  <SelectItem key={ext.id} value={ext.id}>
                    {ext.extension_number}
                    {ext.internal_cid_name ? ` — ${ext.internal_cid_name}` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>{t("bossAdmin.form.assistantExtension")}</Label>
            <Select
              value={assistantExtensionId}
              onValueChange={setAssistantExtensionId}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {availableAssistants.map((ext) => (
                  <SelectItem key={ext.id} value={ext.id}>
                    {ext.extension_number}
                    {ext.internal_cid_name ? ` — ${ext.internal_cid_name}` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </>
      )}

      <div className="space-y-2">
        <Label>{t("bossAdmin.form.filterMode")}</Label>
        <Select value={filterMode} onValueChange={setFilterMode}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {FILTER_MODES.map((mode) => (
              <SelectItem key={mode.value} value={mode.value}>
                {t(mode.labelKey)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {filterMode === "assistant_overflow" && (
        <div className="space-y-2">
          <Label>{t("bossAdmin.form.overflowRingTime")}</Label>
          <Input
            type="number"
            min={5}
            max={120}
            value={overflowRingTime}
            onChange={(e) => setOverflowRingTime(Number(e.target.value))}
          />
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label>{t("bossAdmin.form.dndOverride")}</Label>
          <p className="text-sm text-muted-foreground">
            {t("bossAdmin.form.dndOverrideDescription")}
          </p>
        </div>
        <Switch
          checked={dndOverrideEnabled}
          onCheckedChange={setDndOverrideEnabled}
        />
      </div>

      {filterMode === "vip_bypass" && (
        <div className="space-y-2">
          <Label>{t("bossAdmin.form.vipCallerIds")}</Label>
          <div className="flex gap-2">
            <Input
              value={vipInput}
              onChange={(e) => setVipInput(e.target.value)}
              placeholder={t("bossAdmin.form.vipCallerIdsPlaceholder")}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault()
                  handleAddVip()
                }
              }}
            />
            <Button type="button" variant="outline" onClick={handleAddVip}>
              <Plus className="h-4 w-4" />
            </Button>
          </div>
          {vipCallerIds.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {vipCallerIds.map((id) => (
                <Badge key={id} variant="secondary" className="gap-1">
                  {id}
                  <button
                    type="button"
                    onClick={() => handleRemoveVip(id)}
                    className="ml-1 hover:text-destructive"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
          )}
        </div>
      )}

      {isEditing && (
        <div className="flex items-center justify-between">
          <Label>{t("bossAdmin.form.active")}</Label>
          <Switch checked={isActive} onCheckedChange={setIsActive} />
        </div>
      )}

      <div className="flex justify-end gap-2 pt-4">
        <Button type="submit" disabled={isLoading}>
          {isEditing ? t("common.save") : t("common.create")}
        </Button>
      </div>
    </form>
  )
}

export function BossAdminPage() {
  const { t } = useTranslation()
  const { data: relationships, isLoading, isError, error } = useBossAdminRelationships()
  const { data: extensions } = useExtensions()
  const createMutation = useCreateBossAdminRelationship()
  const updateMutation = useUpdateBossAdminRelationship()
  const deleteMutation = useDeleteBossAdminRelationship()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<BossAdminRelationship | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<BossAdminRelationship | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<BossAdminRelationship[]>([])

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: BossAdminCreate | BossAdminUpdate) => {
    createMutation.mutate(data as BossAdminCreate, {
      onSuccess: () => {
        setDialogOpen(false)
        toast.success(t("toast.created", { item: t("bossAdmin.title") }))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: BossAdminCreate | BossAdminUpdate) => {
    if (!editing) return
    updateMutation.mutate({ id: editing.id, ...(data as BossAdminUpdate) }, {
      onSuccess: () => {
        setDialogOpen(false)
        setEditing(null)
        toast.success(t("toast.updated", { item: t("bossAdmin.title") }))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (rel: BossAdminRelationship) => {
    setDeleting(rel)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: BossAdminRelationship[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: BossAdminRelationship[]) => {
    exportToCsv(
      data,
      [
        { key: "executive_extension_number", label: "Executive" },
        { key: "assistant_extension_number", label: "Assistant" },
        { key: "filter_mode", label: "Filter Mode" },
        { key: "overflow_ring_time", label: "Overflow Ring Time" },
        { key: "dnd_override_enabled", label: "DND Override" },
        { key: "is_active", label: "Active" },
      ],
      "boss-admin-relationships"
    )
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(
            t("toast.bulkDeleted", {
              count: bulkDeleting.length,
              item: t("bossAdmin.title").toLowerCase(),
            })
          )
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => {
        setConfirmOpen(false)
        setDeleting(null)
        toast.success(t("toast.deleted", { item: t("bossAdmin.title") }))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getColumns({
    onEdit: (rel) => {
      setEditing(rel)
      setDialogOpen(true)
    },
    onDelete: handleDelete,
    t,
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("bossAdmin.title")}
        description={t("bossAdmin.description")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Boss Admin" }]}
      >
        <Button
          onClick={() => {
            setEditing(null)
            setDialogOpen(true)
          }}
        >
          <Plus className="mr-2 h-4 w-4" /> {t("bossAdmin.create")}
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
        data={relationships ?? []}
        isLoading={isLoading}
        searchPlaceholder={t("bossAdmin.searchPlaceholder")}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={
          <EmptyState
            icon={UserCog}
            title={t("bossAdmin.emptyTitle")}
            description={t("bossAdmin.emptyDescription")}
            actionLabel={t("bossAdmin.create")}
            onAction={() => {
              setEditing(null)
              setDialogOpen(true)
            }}
          />
        }
      />

      <Dialog
        open={dialogOpen}
        onOpenChange={(open) => {
          if (!open) setEditing(null)
          setDialogOpen(open)
        }}
      >
        <DialogContent
          className="max-w-lg"
          onInteractOutside={(e) => e.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle>
              {editing ? t("bossAdmin.edit") : t("bossAdmin.create")}
            </DialogTitle>
          </DialogHeader>
          <BossAdminForm
            relationship={editing}
            extensions={extensions ?? []}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t("bossAdmin.deleteTitle")}
        description={
          bulkDeleting.length > 0
            ? t("bossAdmin.bulkDeleteConfirm", { count: bulkDeleting.length })
            : t("bossAdmin.deleteConfirm")
        }
        confirmLabel={t("common.delete")}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
