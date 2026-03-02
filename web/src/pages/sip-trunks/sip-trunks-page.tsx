import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useSipTrunks, useCreateSipTrunk, useUpdateSipTrunk, useDeleteSipTrunk, type SIPTrunk, type SIPTrunkCreate } from "@/api/sip-trunks"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getSipTrunkColumns } from "./sip-trunk-columns"
import { SipTrunkForm } from "./sip-trunk-form"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, Network } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

export function SipTrunksPage() {
  const { t } = useTranslation()
  const { data: sipTrunks, isLoading, isError, error } = useSipTrunks()
  const createMutation = useCreateSipTrunk()
  const updateMutation = useUpdateSipTrunk()
  const deleteMutation = useDeleteSipTrunk()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<SIPTrunk | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<SIPTrunk | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<SIPTrunk[]>([])

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: SIPTrunkCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('sipTrunks.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: SIPTrunkCreate) => {
    if (!editing) return
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { password, ...rest } = data as unknown as Record<string, unknown>
    updateMutation.mutate({ id: editing.id, ...rest } as { id: string } & Partial<SIPTrunkCreate>, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('sipTrunks.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (trunk: SIPTrunk) => {
    setDeleting(trunk)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: SIPTrunk[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: SIPTrunk[]) => {
    exportToCsv(data, [
      { key: "name", label: "Name" },
      { key: "host", label: "Host" },
      { key: "transport", label: "Transport" },
      { key: "max_channels", label: "Max Channels" },
    ], "sip-trunks")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t('toast.bulkDeleted', { count: bulkDeleting.length, item: t('sipTrunks.title').toLowerCase() }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('sipTrunks.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getSipTrunkColumns({
    onEdit: (trunk) => { setEditing(trunk); setDialogOpen(true) },
    onDelete: handleDelete,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('sipTrunks.title')} description={t('sipTrunks.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('sipTrunks.title') }]}>
        <Button onClick={() => { setEditing(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('sipTrunks.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        searchPlaceholder={t('sipTrunks.searchPlaceholder')}
        data={sipTrunks ?? []}
        isLoading={isLoading}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={<EmptyState icon={Network} title={t('sipTrunks.emptyTitle')} description={t('sipTrunks.emptyDescription')} actionLabel={t('sipTrunks.create')} onAction={() => { setEditing(null); setDialogOpen(true) }} />}
      />

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) setEditing(null); setDialogOpen(open) }}>
        <DialogContent className="max-w-2xl" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('sipTrunks.edit') : t('sipTrunks.create')}</DialogTitle>
          </DialogHeader>
          <SipTrunkForm
            sipTrunk={editing}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('sipTrunks.deleteTitle')}
        description={
          bulkDeleting.length > 0
            ? t('sipTrunks.bulkDeleteConfirm', { count: bulkDeleting.length })
            : t('sipTrunks.deleteConfirm', { name: deleting?.name })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
