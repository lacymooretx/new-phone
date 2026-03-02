import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useOutboundRoutes, useCreateOutboundRoute, useUpdateOutboundRoute, useDeleteOutboundRoute, type OutboundRoute, type OutboundRouteCreate } from "@/api/outbound-routes"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getOutboundRouteColumns } from "./outbound-route-columns"
import { OutboundRouteForm } from "./outbound-route-form"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, ArrowUpFromLine } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

export function OutboundRoutesPage() {
  const { t } = useTranslation()
  const { data: outboundRoutes, isLoading, isError, error } = useOutboundRoutes()
  const createMutation = useCreateOutboundRoute()
  const updateMutation = useUpdateOutboundRoute()
  const deleteMutation = useDeleteOutboundRoute()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<OutboundRoute | null>(null)
  const [duplicateFrom, setDuplicateFrom] = useState<OutboundRoute | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<OutboundRoute | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<OutboundRoute[]>([])

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: OutboundRouteCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('outboundRoutes.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: OutboundRouteCreate) => {
    if (!editing) return
    updateMutation.mutate({ id: editing.id, ...data }, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('outboundRoutes.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (route: OutboundRoute) => {
    setDeleting(route)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: OutboundRoute[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: OutboundRoute[]) => {
    exportToCsv(data, [
      { key: "name", label: "Name" },
      { key: "dial_pattern", label: "Dial Pattern" },
      { key: "priority", label: "Priority" },
      { key: "enabled", label: "Enabled" },
    ], "outbound-routes")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t('toast.bulkDeleted', { count: bulkDeleting.length, item: t('outboundRoutes.title').toLowerCase() }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('outboundRoutes.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getOutboundRouteColumns({
    onEdit: (route) => { setEditing(route); setDuplicateFrom(null); setDialogOpen(true) },
    onDuplicate: (route) => { setEditing(null); setDuplicateFrom(route); setDialogOpen(true) },
    onDelete: handleDelete,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('outboundRoutes.title')} description={t('outboundRoutes.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('outboundRoutes.title') }]}>
        <Button onClick={() => { setEditing(null); setDuplicateFrom(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('outboundRoutes.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        searchPlaceholder={t('outboundRoutes.searchPlaceholder')}
        data={outboundRoutes ?? []}
        isLoading={isLoading}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={<EmptyState icon={ArrowUpFromLine} title={t('outboundRoutes.emptyTitle')} description={t('outboundRoutes.emptyDescription')} actionLabel={t('outboundRoutes.create')} onAction={() => { setEditing(null); setDuplicateFrom(null); setDialogOpen(true) }} />}
      />

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) { setEditing(null); setDuplicateFrom(null) }; setDialogOpen(open) }}>
        <DialogContent className="max-w-2xl" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('outboundRoutes.edit') : duplicateFrom ? t('outboundRoutes.duplicate') : t('outboundRoutes.create')}</DialogTitle>
          </DialogHeader>
          <OutboundRouteForm
            outboundRoute={editing || duplicateFrom}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('outboundRoutes.deleteTitle')}
        description={
          bulkDeleting.length > 0
            ? t('outboundRoutes.bulkDeleteConfirm', { count: bulkDeleting.length })
            : t('outboundRoutes.deleteConfirm', { name: deleting?.name })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
