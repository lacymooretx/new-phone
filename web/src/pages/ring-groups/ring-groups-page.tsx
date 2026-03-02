import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useRingGroups, useCreateRingGroup, useUpdateRingGroup, useDeleteRingGroup, type RingGroup, type RingGroupCreate } from "@/api/ring-groups"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getRingGroupColumns } from "./ring-group-columns"
import { RingGroupForm } from "./ring-group-form"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, PhoneCall } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

export function RingGroupsPage() {
  const { t } = useTranslation()
  const { data: ringGroups, isLoading, isError, error } = useRingGroups()
  const createMutation = useCreateRingGroup()
  const updateMutation = useUpdateRingGroup()
  const deleteMutation = useDeleteRingGroup()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<RingGroup | null>(null)
  const [duplicateFrom, setDuplicateFrom] = useState<RingGroup | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<RingGroup | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<RingGroup[]>([])

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: RingGroupCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('ringGroups.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: RingGroupCreate) => {
    if (!editing) return
    updateMutation.mutate({ id: editing.id, ...data }, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('ringGroups.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (rg: RingGroup) => {
    setDeleting(rg)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: RingGroup[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: RingGroup[]) => {
    exportToCsv(data, [
      { key: "group_number", label: "Group Number" },
      { key: "name", label: "Name" },
      { key: "strategy", label: "Strategy" },
      { key: "is_active", label: "Active" },
    ], "ring-groups")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t('toast.bulkDeleted', { count: bulkDeleting.length, item: t('ringGroups.title').toLowerCase() }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('ringGroups.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getRingGroupColumns({
    onEdit: (rg) => { setEditing(rg); setDuplicateFrom(null); setDialogOpen(true) },
    onDuplicate: (rg) => { setEditing(null); setDuplicateFrom(rg); setDialogOpen(true) },
    onDelete: handleDelete,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('ringGroups.title')} description={t('ringGroups.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('ringGroups.title') }]}>
        <Button onClick={() => { setEditing(null); setDuplicateFrom(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('ringGroups.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        data={ringGroups ?? []}
        isLoading={isLoading}
        searchPlaceholder={t('ringGroups.searchPlaceholder')}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={<EmptyState icon={PhoneCall} title={t('ringGroups.emptyTitle')} description={t('ringGroups.emptyDescription')} actionLabel={t('ringGroups.create')} onAction={() => { setEditing(null); setDuplicateFrom(null); setDialogOpen(true) }} />}
      />

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) { setEditing(null); setDuplicateFrom(null) }; setDialogOpen(open) }}>
        <DialogContent className="max-w-3xl" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('ringGroups.edit') : duplicateFrom ? t('ringGroups.duplicate') : t('ringGroups.create')}</DialogTitle>
          </DialogHeader>
          <RingGroupForm
            ringGroup={editing || duplicateFrom}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('ringGroups.deleteTitle')}
        description={
          bulkDeleting.length > 0
            ? t('ringGroups.bulkDeleteConfirm', { count: bulkDeleting.length })
            : t('ringGroups.deleteConfirm', { name: deleting?.name })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
