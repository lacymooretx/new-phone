import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useForm } from "react-hook-form"
import {
  useSites,
  useCreateSite,
  useUpdateSite,
  useDeleteSite,
  type Site,
  type SiteCreate,
} from "@/api/sites"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { EmptyState } from "@/components/shared/empty-state"
import { StatusBadge } from "@/components/shared/status-badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Separator } from "@/components/ui/separator"
import { Plus, Building2 } from "lucide-react"
import { toast } from "sonner"
import { exportToCsv } from "@/lib/export-csv"
import type { ColumnDef } from "@tanstack/react-table"
import i18next from "i18next"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { MoreHorizontal, Pencil, Trash2 } from "lucide-react"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"

function getSiteColumns(actions: {
  onEdit: (site: Site) => void
  onDelete: (site: Site) => void
}): ColumnDef<Site, unknown>[] {
  return [
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t("sites.col.name")} />,
    },
    {
      accessorKey: "timezone",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t("sites.col.timezone")} />,
    },
    {
      id: "location",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t("sites.col.location")} />,
      cell: ({ row }) => {
        const s = row.original
        const parts = [s.address_city, s.address_state].filter(Boolean)
        return parts.length > 0 ? parts.join(", ") : "—"
      },
    },
    {
      id: "outbound_cid",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t("sites.col.outboundCid")} />,
      cell: ({ row }) => {
        const s = row.original
        if (s.outbound_cid_name && s.outbound_cid_number)
          return `${s.outbound_cid_name} <${s.outbound_cid_number}>`
        return s.outbound_cid_number || s.outbound_cid_name || "—"
      },
    },
    {
      accessorKey: "is_active",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t("common.status")} />,
      cell: ({ row }) => (
        <StatusBadge
          active={row.original.is_active}
          activeLabel={i18next.t("common.active")}
          inactiveLabel={i18next.t("common.inactive")}
        />
      ),
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0" aria-label="Actions">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => actions.onEdit(row.original)}>
              <Pencil className="mr-2 h-4 w-4" /> {i18next.t("common.edit")}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => actions.onDelete(row.original)} className="text-destructive">
              <Trash2 className="mr-2 h-4 w-4" /> {i18next.t("common.delete")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]
}

interface SiteFormProps {
  site?: Site | null
  onSubmit: (data: SiteCreate) => void
  isLoading: boolean
}

function SiteForm({ site, onSubmit, isLoading }: SiteFormProps) {
  const { t } = useTranslation()
  const { register, handleSubmit, formState: { errors } } = useForm<SiteCreate>({
    defaultValues: {
      name: site?.name ?? "",
      description: site?.description ?? "",
      timezone: site?.timezone ?? "America/New_York",
      address_street: site?.address_street ?? "",
      address_city: site?.address_city ?? "",
      address_state: site?.address_state ?? "",
      address_zip: site?.address_zip ?? "",
      address_country: site?.address_country ?? "US",
      outbound_cid_name: site?.outbound_cid_name ?? "",
      outbound_cid_number: site?.outbound_cid_number ?? "",
    },
  })

  const submitHandler = (values: SiteCreate) => {
    onSubmit({
      ...values,
      description: values.description || undefined,
      address_street: values.address_street || undefined,
      address_city: values.address_city || undefined,
      address_state: values.address_state || undefined,
      address_zip: values.address_zip || undefined,
      outbound_cid_name: values.outbound_cid_name || undefined,
      outbound_cid_number: values.outbound_cid_number || undefined,
    })
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">{t("sites.form.name")} *</Label>
          <Input id="name" {...register("name", { required: t("common.required") })} placeholder={t("sites.form.namePlaceholder")} />
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="timezone">{t("sites.form.timezone")} *</Label>
          <Input id="timezone" {...register("timezone", { required: t("common.required") })} placeholder="America/New_York" />
          {errors.timezone && <p className="text-xs text-destructive">{errors.timezone.message}</p>}
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">{t("common.description")}</Label>
        <Textarea id="description" {...register("description")} />
      </div>

      <Separator />
      <h3 className="text-sm font-medium">{t("sites.form.address")}</h3>

      <div className="space-y-2">
        <Label htmlFor="address_street">{t("sites.form.street")}</Label>
        <Input id="address_street" {...register("address_street")} placeholder={t("sites.form.streetPlaceholder")} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <div className="space-y-2">
          <Label htmlFor="address_city">{t("sites.form.city")}</Label>
          <Input id="address_city" {...register("address_city")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="address_state">{t("sites.form.state")}</Label>
          <Input id="address_state" {...register("address_state")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="address_zip">{t("sites.form.zip")}</Label>
          <Input id="address_zip" {...register("address_zip")} />
        </div>
      </div>

      <div className="max-w-xs space-y-2">
        <Label htmlFor="address_country">{t("sites.form.country")}</Label>
        <Input id="address_country" {...register("address_country")} placeholder="US" />
      </div>

      <Separator />
      <h3 className="text-sm font-medium">{t("sites.form.callerIdSection")}</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="outbound_cid_name">{t("sites.form.cidName")}</Label>
          <Input id="outbound_cid_name" {...register("outbound_cid_name")} placeholder={t("sites.form.cidNamePlaceholder")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="outbound_cid_number">{t("sites.form.cidNumber")}</Label>
          <Input id="outbound_cid_number" {...register("outbound_cid_number")} type="tel" placeholder={t("sites.form.cidNumberPlaceholder")} />
        </div>
      </div>

      <div className="flex justify-end gap-2 pt-4">
        <Button type="submit" disabled={isLoading}>
          {isLoading ? t("common.saving") : site ? t("common.save") : t("common.create")}
        </Button>
      </div>
    </form>
  )
}

export function SitesPage() {
  const { t } = useTranslation()
  const { data: sites, isLoading, isError, error } = useSites()
  const createMutation = useCreateSite()
  const updateMutation = useUpdateSite()
  const deleteMutation = useDeleteSite()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Site | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<Site | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<Site[]>([])

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: SiteCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t("toast.created", { item: t("sites.title") })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: SiteCreate) => {
    if (!editing) return
    updateMutation.mutate({ id: editing.id, ...data }, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t("toast.updated", { item: t("sites.title") })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (site: Site) => { setDeleting(site); setConfirmOpen(true) }
  const handleBulkDelete = (rows: Site[]) => { setBulkDeleting(rows); setConfirmOpen(true) }

  const handleExport = (data: Site[]) => {
    exportToCsv(data, [
      { key: "name", label: "Name" },
      { key: "timezone", label: "Timezone" },
      { key: "address_city", label: "City" },
      { key: "address_state", label: "State" },
      { key: "address_country", label: "Country" },
      { key: "outbound_cid_name", label: "CID Name" },
      { key: "outbound_cid_number", label: "CID Number" },
      { key: "is_active", label: "Active" },
    ], "sites")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t("toast.bulkDeleted", { count: bulkDeleting.length, item: t("sites.title").toLowerCase() }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t("toast.deleted", { item: t("sites.title") })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getSiteColumns({
    onEdit: (site) => { setEditing(site); setDialogOpen(true) },
    onDelete: handleDelete,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t("sites.title")} description={t("sites.description")} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t("sites.title") }]}>
        <Button onClick={() => { setEditing(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t("sites.create")}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t("common.failedToLoad", { message: error?.message || t("common.unknownError") })}
        </div>
      )}

      <DataTable
        columns={columns}
        data={sites ?? []}
        isLoading={isLoading}
        searchPlaceholder={t("sites.searchPlaceholder")}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={
          <EmptyState
            icon={Building2}
            title={t("sites.emptyTitle")}
            description={t("sites.emptyDescription")}
            actionLabel={t("sites.create")}
            onAction={() => { setEditing(null); setDialogOpen(true) }}
          />
        }
      />

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) setEditing(null); setDialogOpen(open) }}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t("sites.edit") : t("sites.create")}</DialogTitle>
          </DialogHeader>
          <SiteForm
            site={editing}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t("sites.deleteTitle")}
        description={
          bulkDeleting.length > 0
            ? t("sites.bulkDeleteConfirm", { count: bulkDeleting.length })
            : t("sites.deleteConfirm", { name: deleting?.name })
        }
        confirmLabel={t("common.delete")}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
