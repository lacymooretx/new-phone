import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useQueues, useCreateQueue, useUpdateQueue, useDeleteQueue, type Queue, type QueueCreate } from "@/api/queues"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getQueueColumns } from "./queue-columns"
import { QueueForm } from "./queue-form"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, ListOrdered } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

export function QueuesPage() {
  const { t } = useTranslation()
  const { data: queues, isLoading, isError, error } = useQueues()
  const createMutation = useCreateQueue()
  const updateMutation = useUpdateQueue()
  const deleteMutation = useDeleteQueue()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Queue | null>(null)
  const [duplicateFrom, setDuplicateFrom] = useState<Queue | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<Queue | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<Queue[]>([])

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: QueueCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('queues.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: QueueCreate) => {
    if (!editing) return
    updateMutation.mutate({ id: editing.id, ...data }, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('queues.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (queue: Queue) => {
    setDeleting(queue)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: Queue[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: Queue[]) => {
    exportToCsv(data, [
      { key: "queue_number", label: "Queue Number" },
      { key: "name", label: "Name" },
      { key: "strategy", label: "Strategy" },
      { key: "is_active", label: "Active" },
    ], "queues")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t('toast.bulkDeleted', { count: bulkDeleting.length, item: t('queues.title').toLowerCase() }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('queues.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getQueueColumns({
    onEdit: (queue) => { setEditing(queue); setDuplicateFrom(null); setDialogOpen(true) },
    onDuplicate: (queue) => { setEditing(null); setDuplicateFrom(queue); setDialogOpen(true) },
    onDelete: handleDelete,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('queues.title')} description={t('queues.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('queues.title') }]}>
        <Button onClick={() => { setEditing(null); setDuplicateFrom(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('queues.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        data={queues ?? []}
        isLoading={isLoading}
        searchPlaceholder={t('queues.searchPlaceholder')}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={<EmptyState icon={ListOrdered} title={t('queues.emptyTitle')} description={t('queues.emptyDescription')} actionLabel={t('queues.create')} onAction={() => { setEditing(null); setDuplicateFrom(null); setDialogOpen(true) }} />}
      />

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) { setEditing(null); setDuplicateFrom(null) }; setDialogOpen(open) }}>
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('queues.edit') : duplicateFrom ? t('queues.duplicate') : t('queues.create')}</DialogTitle>
          </DialogHeader>
          <QueueForm
            queue={editing || duplicateFrom}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('queues.deleteTitle')}
        description={
          bulkDeleting.length > 0
            ? t('queues.bulkDeleteConfirm', { count: bulkDeleting.length })
            : t('queues.deleteConfirm', { name: deleting?.name })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
