import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useDids, useCreateDid, useUpdateDid, useDeleteDid, useReleaseDid, type DID, type DIDCreate } from "@/api/dids"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getDidColumns } from "./did-columns"
import { DidForm } from "./did-form"
import { DidMarketplaceDialog } from "./did-marketplace-dialog"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, Hash, ShoppingCart } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

export function DidsPage() {
  const { t } = useTranslation()
  const { data: dids, isLoading, isError, error } = useDids()
  const createMutation = useCreateDid()
  const updateMutation = useUpdateDid()
  const deleteMutation = useDeleteDid()
  const releaseMutation = useReleaseDid()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [marketplaceOpen, setMarketplaceOpen] = useState(false)
  const [editing, setEditing] = useState<DID | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<DID | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<DID[]>([])
  const [releasing, setReleasing] = useState<DID | null>(null)

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: DIDCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('dids.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: DIDCreate) => {
    if (!editing) return
    updateMutation.mutate({ id: editing.id, ...data }, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('dids.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (did: DID) => {
    setDeleting(did)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: DID[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: DID[]) => {
    exportToCsv(data, [
      { key: "number", label: "Number" },
      { key: "provider", label: "Provider" },
      { key: "did_status", label: "Status" },
      { key: "is_active", label: "Active" },
    ], "dids")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t('toast.bulkDeleted', { count: bulkDeleting.length, item: t('dids.title').toLowerCase() }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('dids.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleRelease = (did: DID) => {
    setReleasing(did)
  }

  const confirmRelease = () => {
    if (!releasing) return
    releaseMutation.mutate(releasing.id, {
      onSuccess: () => {
        setReleasing(null)
        toast.success(t("dids.releaseSuccess"))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getDidColumns({
    onEdit: (did) => { setEditing(did); setDialogOpen(true) },
    onDelete: handleDelete,
    onRelease: handleRelease,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('dids.title')} description={t('dids.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('dids.title') }]}>
        <Button variant="outline" onClick={() => setMarketplaceOpen(true)}>
          <ShoppingCart className="mr-2 h-4 w-4" /> {t('dids.buyNumbers')}
        </Button>
        <Button onClick={() => { setEditing(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('dids.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        data={dids ?? []}
        isLoading={isLoading}
        searchPlaceholder={t('dids.searchPlaceholder')}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={<EmptyState icon={Hash} title={t('dids.emptyTitle')} description={t('dids.emptyDescription')} actionLabel={t('dids.create')} onAction={() => { setEditing(null); setDialogOpen(true) }} />}
      />

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('dids.edit') : t('dids.create')}</DialogTitle>
          </DialogHeader>
          <DidForm
            did={editing}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('dids.deleteTitle')}
        description={
          bulkDeleting.length > 0
            ? t('dids.bulkDeleteConfirm', { count: bulkDeleting.length })
            : t('dids.deleteConfirm', { number: deleting?.number })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />

      <DidMarketplaceDialog open={marketplaceOpen} onOpenChange={setMarketplaceOpen} />

      <ConfirmDialog
        open={!!releasing}
        onOpenChange={(open) => { if (!open) setReleasing(null) }}
        title={t('dids.releaseTitle')}
        description={t('dids.releaseConfirm', { number: releasing?.number })}
        confirmLabel={t('dids.releaseButton')}
        variant="destructive"
        onConfirm={confirmRelease}
      />
    </div>
  )
}
