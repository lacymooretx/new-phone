import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useInboundRoutes, useCreateInboundRoute, useUpdateInboundRoute, useDeleteInboundRoute, type InboundRoute, type InboundRouteCreate } from "@/api/inbound-routes"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getInboundRouteColumns } from "./inbound-route-columns"
import { InboundRouteForm } from "./inbound-route-form"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, ArrowDownToLine } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

export function InboundRoutesPage() {
  const { t } = useTranslation()
  const { data: inboundRoutes, isLoading, isError, error } = useInboundRoutes()
  const createMutation = useCreateInboundRoute()
  const updateMutation = useUpdateInboundRoute()
  const deleteMutation = useDeleteInboundRoute()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<InboundRoute | null>(null)
  const [duplicateFrom, setDuplicateFrom] = useState<InboundRoute | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<InboundRoute | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<InboundRoute[]>([])

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: InboundRouteCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('inboundRoutes.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: InboundRouteCreate) => {
    if (!editing) return
    updateMutation.mutate({ id: editing.id, ...data }, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('inboundRoutes.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (route: InboundRoute) => {
    setDeleting(route)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: InboundRoute[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: InboundRoute[]) => {
    exportToCsv(data, [
      { key: "name", label: "Name" },
      { key: "did_pattern", label: "DID Pattern" },
      { key: "cid_pattern", label: "CID Pattern" },
      { key: "destination_type", label: "Destination Type" },
    ], "inbound-routes")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t('toast.bulkDeleted', { count: bulkDeleting.length, item: t('inboundRoutes.title').toLowerCase() }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('inboundRoutes.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getInboundRouteColumns({
    onEdit: (route) => { setEditing(route); setDuplicateFrom(null); setDialogOpen(true) },
    onDuplicate: (route) => { setEditing(null); setDuplicateFrom(route); setDialogOpen(true) },
    onDelete: handleDelete,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('inboundRoutes.title')} description={t('inboundRoutes.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('inboundRoutes.title') }]}>
        <Button onClick={() => { setEditing(null); setDuplicateFrom(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('inboundRoutes.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        searchPlaceholder={t('inboundRoutes.searchPlaceholder')}
        data={inboundRoutes ?? []}
        isLoading={isLoading}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={<EmptyState icon={ArrowDownToLine} title={t('inboundRoutes.emptyTitle')} description={t('inboundRoutes.emptyDescription')} actionLabel={t('inboundRoutes.create')} onAction={() => { setEditing(null); setDuplicateFrom(null); setDialogOpen(true) }} />}
      />

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) { setEditing(null); setDuplicateFrom(null) }; setDialogOpen(open) }}>
        <DialogContent className="max-w-2xl" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('inboundRoutes.edit') : duplicateFrom ? t('inboundRoutes.duplicate') : t('inboundRoutes.create')}</DialogTitle>
          </DialogHeader>
          <InboundRouteForm
            inboundRoute={editing || duplicateFrom}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('inboundRoutes.deleteTitle')}
        description={
          bulkDeleting.length > 0
            ? t('inboundRoutes.bulkDeleteConfirm', { count: bulkDeleting.length })
            : t('inboundRoutes.deleteConfirm', { name: deleting?.name })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
