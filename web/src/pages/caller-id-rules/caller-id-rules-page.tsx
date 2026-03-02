import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useCallerIdRules, useCreateCallerIdRule, useUpdateCallerIdRule, useDeleteCallerIdRule, type CallerIdRule, type CallerIdRuleCreate } from "@/api/caller-id-rules"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getCallerIdRuleColumns } from "./caller-id-rule-columns"
import { CallerIdRuleForm } from "./caller-id-rule-form"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, Shield } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

export function CallerIdRulesPage() {
  const { t } = useTranslation()
  const { data: rules, isLoading, isError, error } = useCallerIdRules()
  const createMutation = useCreateCallerIdRule()
  const updateMutation = useUpdateCallerIdRule()
  const deleteMutation = useDeleteCallerIdRule()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<CallerIdRule | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<CallerIdRule | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<CallerIdRule[]>([])

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: CallerIdRuleCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('callerIdRules.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: CallerIdRuleCreate) => {
    if (!editing) return
    updateMutation.mutate({ id: editing.id, ...data }, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('callerIdRules.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (rule: CallerIdRule) => {
    setDeleting(rule)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: CallerIdRule[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: CallerIdRule[]) => {
    exportToCsv(data, [
      { key: "name", label: t('callerIdRules.col.name') },
      { key: "pattern", label: t('callerIdRules.col.matchPattern') },
      { key: "type", label: t('common.type') },
      { key: "priority", label: t('callerIdRules.col.priority') },
    ], "caller-id-rules")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t('toast.bulkDeleted', { count: bulkDeleting.length, item: t('callerIdRules.title') }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('callerIdRules.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getCallerIdRuleColumns({
    onEdit: (rule) => { setEditing(rule); setDialogOpen(true) },
    onDelete: handleDelete,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('callerIdRules.title')} description={t('callerIdRules.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('callerIdRules.title') }]}>
        <Button onClick={() => { setEditing(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('callerIdRules.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        searchPlaceholder={t('callerIdRules.searchPlaceholder')}
        data={rules ?? []}
        isLoading={isLoading}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={<EmptyState icon={Shield} title={t('callerIdRules.emptyTitle')} description={t('callerIdRules.emptyDescription')} actionLabel={t('callerIdRules.create')} onAction={() => { setEditing(null); setDialogOpen(true) }} />}
      />

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('callerIdRules.edit') : t('callerIdRules.create')}</DialogTitle>
          </DialogHeader>
          <CallerIdRuleForm
            callerIdRule={editing}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('callerIdRules.deleteTitle')}
        description={
          bulkDeleting.length > 0
            ? t('callerIdRules.bulkDeleteConfirm', { count: bulkDeleting.length })
            : t('callerIdRules.deleteConfirm', { name: deleting?.name })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
