import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useConferences, useCreateConference, useUpdateConference, useDeleteConference, type ConferenceBridge, type ConferenceBridgeCreate } from "@/api/conferences"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getConferenceColumns } from "./conference-columns"
import { ConferenceForm } from "./conference-form"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, Video } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

export function ConferencesPage() {
  const { t } = useTranslation()
  const { data: conferences, isLoading, isError, error } = useConferences()
  const createMutation = useCreateConference()
  const updateMutation = useUpdateConference()
  const deleteMutation = useDeleteConference()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<ConferenceBridge | null>(null)
  const [duplicateFrom, setDuplicateFrom] = useState<ConferenceBridge | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<ConferenceBridge | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<ConferenceBridge[]>([])

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: ConferenceBridgeCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('conferences.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: ConferenceBridgeCreate) => {
    if (!editing) return
    updateMutation.mutate({ id: editing.id, ...data }, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('conferences.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (conf: ConferenceBridge) => {
    setDeleting(conf)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: ConferenceBridge[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: ConferenceBridge[]) => {
    exportToCsv(data, [
      { key: "room_number", label: "Room Number" },
      { key: "name", label: "Name" },
      { key: "max_participants", label: "Max Participants" },
      { key: "is_active", label: "Active" },
    ], "conferences")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t('toast.bulkDeleted', { count: bulkDeleting.length, item: t('conferences.title').toLowerCase() }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('conferences.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getConferenceColumns({
    onEdit: (conf) => { setEditing(conf); setDuplicateFrom(null); setDialogOpen(true) },
    onDuplicate: (conf) => { setEditing(null); setDuplicateFrom(conf); setDialogOpen(true) },
    onDelete: handleDelete,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('conferences.title')} description={t('conferences.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('conferences.title') }]}>
        <Button onClick={() => { setEditing(null); setDuplicateFrom(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('conferences.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        searchPlaceholder={t('conferences.searchPlaceholder')}
        data={conferences ?? []}
        isLoading={isLoading}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={<EmptyState icon={Video} title={t('conferences.emptyTitle')} description={t('conferences.emptyDescription')} actionLabel={t('conferences.create')} onAction={() => { setEditing(null); setDuplicateFrom(null); setDialogOpen(true) }} />}
      />

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) { setEditing(null); setDuplicateFrom(null) }; setDialogOpen(open) }}>
        <DialogContent className="max-w-2xl" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('conferences.edit') : duplicateFrom ? t('conferences.duplicate') : t('conferences.create')}</DialogTitle>
          </DialogHeader>
          <ConferenceForm
            conference={editing || duplicateFrom}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('conferences.deleteTitle')}
        description={
          bulkDeleting.length > 0
            ? t('conferences.bulkDeleteConfirm', { count: bulkDeleting.length })
            : t('conferences.deleteConfirm', { name: deleting?.name })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
