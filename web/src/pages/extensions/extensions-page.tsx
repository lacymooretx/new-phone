import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useExtensions, useCreateExtension, useUpdateExtension, useDeleteExtension, type Extension, type ExtensionCreate } from "@/api/extensions"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getExtensionColumns } from "./extension-columns"
import { ExtensionForm } from "./extension-form"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, Phone } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

export function ExtensionsPage() {
  const { t } = useTranslation()
  const { data: extensions, isLoading, isError, error } = useExtensions()
  const createMutation = useCreateExtension()
  const updateMutation = useUpdateExtension()
  const deleteMutation = useDeleteExtension()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Extension | null>(null)
  const [duplicateFrom, setDuplicateFrom] = useState<Extension | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<Extension | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<Extension[]>([])

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: ExtensionCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('extensions.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: ExtensionCreate) => {
    if (!editing) return
    updateMutation.mutate({ id: editing.id, ...data }, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('extensions.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (ext: Extension) => {
    setDeleting(ext)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: Extension[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: Extension[]) => {
    exportToCsv(data, [
      { key: "extension_number", label: "Extension Number" },
      { key: "internal_cid_name", label: "Internal CID Name" },
      { key: "is_active", label: "Active" },
      { key: "class_of_service", label: "Class of Service" },
    ], "extensions")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t('toast.bulkDeleted', { count: bulkDeleting.length, item: t('extensions.title').toLowerCase() }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('extensions.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getExtensionColumns({
    onEdit: (ext) => { setEditing(ext); setDuplicateFrom(null); setDialogOpen(true) },
    onDuplicate: (ext) => { setEditing(null); setDuplicateFrom(ext); setDialogOpen(true) },
    onDelete: handleDelete,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('extensions.title')} description={t('extensions.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('extensions.title') }]}>
        <Button onClick={() => { setEditing(null); setDuplicateFrom(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('extensions.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        data={extensions ?? []}
        isLoading={isLoading}
        searchPlaceholder={t('extensions.searchPlaceholder')}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={<EmptyState icon={Phone} title={t('extensions.emptyTitle')} description={t('extensions.emptyDescription')} actionLabel={t('extensions.create')} onAction={() => { setEditing(null); setDuplicateFrom(null); setDialogOpen(true) }} />}
      />

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) { setEditing(null); setDuplicateFrom(null) }; setDialogOpen(open) }}>
        <DialogContent className="max-w-2xl" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('extensions.edit') : duplicateFrom ? t('extensions.duplicate') : t('extensions.create')}</DialogTitle>
          </DialogHeader>
          <ExtensionForm
            extension={editing || duplicateFrom}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('extensions.deleteTitle')}
        description={
          bulkDeleting.length > 0
            ? t('extensions.bulkDeleteConfirm', { count: bulkDeleting.length })
            : t('extensions.deleteConfirm', { number: deleting?.extension_number })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
