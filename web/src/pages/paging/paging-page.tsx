import { useState } from "react"
import { useTranslation } from "react-i18next"
import { usePageGroups, useCreatePageGroup, useUpdatePageGroup, useDeletePageGroup, type PageGroup, type PageGroupCreate } from "@/api/page-groups"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getPageGroupColumns } from "./page-group-columns"
import { PageGroupForm } from "./page-group-form"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, Megaphone } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

export function PagingPage() {
  const { t } = useTranslation()
  const { data: pageGroups, isLoading, isError, error } = usePageGroups()
  const createMutation = useCreatePageGroup()
  const updateMutation = useUpdatePageGroup()
  const deleteMutation = useDeletePageGroup()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<PageGroup | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<PageGroup | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<PageGroup[]>([])

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: PageGroupCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('paging.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: PageGroupCreate) => {
    if (!editing) return
    updateMutation.mutate({ id: editing.id, ...data }, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('paging.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (pg: PageGroup) => {
    setDeleting(pg)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: PageGroup[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: PageGroup[]) => {
    exportToCsv(data, [
      { key: "page_number", label: "Page Number" },
      { key: "name", label: "Name" },
      { key: "mode", label: "Mode" },
      { key: "is_active", label: "Active" },
    ], "paging-groups")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t('toast.bulkDeleted', { count: bulkDeleting.length, item: t('paging.title').toLowerCase() }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('paging.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getPageGroupColumns({
    onEdit: (pg) => { setEditing(pg); setDialogOpen(true) },
    onDelete: handleDelete,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('paging.title')} description={t('paging.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('paging.title') }]}>
        <Button onClick={() => { setEditing(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('paging.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        searchPlaceholder={t('paging.searchPlaceholder')}
        data={pageGroups ?? []}
        isLoading={isLoading}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={<EmptyState icon={Megaphone} title={t('paging.emptyTitle')} description={t('paging.emptyDescription')} actionLabel={t('paging.create')} onAction={() => { setEditing(null); setDialogOpen(true) }} />}
      />

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) setEditing(null); setDialogOpen(open) }}>
        <DialogContent className="max-w-3xl" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('paging.edit') : t('paging.create')}</DialogTitle>
          </DialogHeader>
          <PageGroupForm
            pageGroup={editing}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('paging.deleteTitle')}
        description={
          bulkDeleting.length > 0
            ? t('paging.bulkDeleteConfirm', { count: bulkDeleting.length })
            : t('paging.deleteConfirm', { name: deleting?.name })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
