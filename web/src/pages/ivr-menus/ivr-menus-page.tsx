import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useIvrMenus, useCreateIvrMenu, useUpdateIvrMenu, useDeleteIvrMenu, type IVRMenu, type IVRMenuCreate } from "@/api/ivr-menus"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getIvrMenuColumns } from "./ivr-menu-columns"
import { IvrMenuForm } from "./ivr-menu-form"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, Menu } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

export function IvrMenusPage() {
  const { t } = useTranslation()
  const { data: ivrMenus, isLoading, isError, error } = useIvrMenus()
  const createMutation = useCreateIvrMenu()
  const updateMutation = useUpdateIvrMenu()
  const deleteMutation = useDeleteIvrMenu()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<IVRMenu | null>(null)
  const [duplicateFrom, setDuplicateFrom] = useState<IVRMenu | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<IVRMenu | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<IVRMenu[]>([])

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: IVRMenuCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('ivrMenus.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: IVRMenuCreate) => {
    if (!editing) return
    updateMutation.mutate({ id: editing.id, ...data }, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('ivrMenus.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (menu: IVRMenu) => {
    setDeleting(menu)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: IVRMenu[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: IVRMenu[]) => {
    exportToCsv(data, [
      { key: "name", label: "Name" },
      { key: "description", label: "Description" },
      { key: "is_active", label: "Active" },
    ], "ivr-menus")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t('toast.bulkDeleted', { count: bulkDeleting.length, item: t('ivrMenus.title').toLowerCase() }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('ivrMenus.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getIvrMenuColumns({
    onEdit: (menu) => { setEditing(menu); setDuplicateFrom(null); setDialogOpen(true) },
    onDuplicate: (menu) => { setEditing(null); setDuplicateFrom(menu); setDialogOpen(true) },
    onDelete: handleDelete,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('ivrMenus.title')} description={t('ivrMenus.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('ivrMenus.title') }]}>
        <Button onClick={() => { setEditing(null); setDuplicateFrom(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('ivrMenus.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        searchPlaceholder={t('ivrMenus.searchPlaceholder')}
        data={ivrMenus ?? []}
        isLoading={isLoading}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={<EmptyState icon={Menu} title={t('ivrMenus.emptyTitle')} description={t('ivrMenus.emptyDescription')} actionLabel={t('ivrMenus.create')} onAction={() => { setEditing(null); setDuplicateFrom(null); setDialogOpen(true) }} />}
      />

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) { setEditing(null); setDuplicateFrom(null) }; setDialogOpen(open) }}>
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('ivrMenus.edit') : duplicateFrom ? t('ivrMenus.duplicate') : t('ivrMenus.create')}</DialogTitle>
          </DialogHeader>
          <IvrMenuForm
            ivrMenu={editing || duplicateFrom}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('ivrMenus.deleteTitle')}
        description={
          bulkDeleting.length > 0
            ? t('ivrMenus.bulkDeleteConfirm', { count: bulkDeleting.length })
            : t('ivrMenus.deleteConfirm', { name: deleting?.name })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
