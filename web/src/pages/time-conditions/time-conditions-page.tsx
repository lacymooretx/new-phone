import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useTimeConditions, useCreateTimeCondition, useUpdateTimeCondition, useDeleteTimeCondition, type TimeCondition, type TimeConditionCreate } from "@/api/time-conditions"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getTimeConditionColumns } from "./time-condition-columns"
import { TimeConditionForm } from "./time-condition-form"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, Clock } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

export function TimeConditionsPage() {
  const { t } = useTranslation()
  const { data: timeConditions, isLoading, isError, error } = useTimeConditions()
  const createMutation = useCreateTimeCondition()
  const updateMutation = useUpdateTimeCondition()
  const deleteMutation = useDeleteTimeCondition()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<TimeCondition | null>(null)
  const [duplicateFrom, setDuplicateFrom] = useState<TimeCondition | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<TimeCondition | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<TimeCondition[]>([])

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: TimeConditionCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('timeConditions.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: TimeConditionCreate) => {
    if (!editing) return
    updateMutation.mutate({ id: editing.id, ...data }, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('timeConditions.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (tc: TimeCondition) => {
    setDeleting(tc)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: TimeCondition[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: TimeCondition[]) => {
    exportToCsv(data, [
      { key: "name", label: t('timeConditions.col.name') },
      { key: "timezone", label: t('timeConditions.col.timezone') },
      { key: "enabled", label: t('common.enabled') },
    ], "time-conditions")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t('toast.bulkDeleted', { count: bulkDeleting.length, item: t('timeConditions.title') }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('timeConditions.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getTimeConditionColumns({
    onEdit: (tc) => { setEditing(tc); setDuplicateFrom(null); setDialogOpen(true) },
    onDuplicate: (tc) => { setEditing(null); setDuplicateFrom(tc); setDialogOpen(true) },
    onDelete: handleDelete,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('timeConditions.title')} description={t('timeConditions.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('timeConditions.title') }]}>
        <Button onClick={() => { setEditing(null); setDuplicateFrom(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('timeConditions.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        searchPlaceholder={t('timeConditions.searchPlaceholder')}
        data={timeConditions ?? []}
        isLoading={isLoading}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={<EmptyState icon={Clock} title={t('timeConditions.emptyTitle')} description={t('timeConditions.emptyDescription')} actionLabel={t('timeConditions.create')} onAction={() => { setEditing(null); setDuplicateFrom(null); setDialogOpen(true) }} />}
      />

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) { setEditing(null); setDuplicateFrom(null) }; setDialogOpen(open) }}>
        <DialogContent className="max-w-3xl" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('timeConditions.edit') : duplicateFrom ? t('common.duplicate') : t('timeConditions.create')}</DialogTitle>
          </DialogHeader>
          <TimeConditionForm
            timeCondition={editing || duplicateFrom}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('timeConditions.deleteTitle')}
        description={
          bulkDeleting.length > 0
            ? t('timeConditions.bulkDeleteConfirm', { count: bulkDeleting.length })
            : t('timeConditions.deleteConfirm', { name: deleting?.name })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
