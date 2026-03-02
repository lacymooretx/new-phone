import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useUsers, useCreateUser, useUpdateUser, useDeleteUser, type User, type UserCreate } from "@/api/users"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getUserColumns } from "./user-columns"
import { UserForm } from "./user-form"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, Users as UsersIcon } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

export function UsersPage() {
  const { t } = useTranslation()
  const { data: users, isLoading, isError, error } = useUsers()
  const createMutation = useCreateUser()
  const updateMutation = useUpdateUser()
  const deleteMutation = useDeleteUser()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<User | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<User | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<User[]>([])

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: UserCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('users.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: UserCreate) => {
    if (!editing) return
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { password, ...rest } = data as unknown as Record<string, unknown>
    updateMutation.mutate({ id: editing.id, ...rest } as { id: string } & import("@/api/users").UserUpdate, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('users.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (user: User) => {
    setDeleting(user)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: User[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: User[]) => {
    exportToCsv(data, [
      { key: "email", label: t('users.col.email') },
      { key: "first_name", label: t('users.form.firstName') },
      { key: "last_name", label: t('users.form.lastName') },
      { key: "role", label: t('users.col.role') },
      { key: "is_active", label: t('common.active') },
    ], "users")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t('toast.bulkDeleted', { count: bulkDeleting.length, item: t('users.title') }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('users.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getUserColumns({
    onEdit: (u) => { setEditing(u); setDialogOpen(true) },
    onDelete: handleDelete,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('users.title')} description={t('users.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('users.title') }]}>
        <Button onClick={() => { setEditing(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('users.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        data={users ?? []}
        isLoading={isLoading}
        searchPlaceholder={t('users.searchPlaceholder')}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={<EmptyState icon={UsersIcon} title={t('users.emptyTitle')} description={t('users.emptyDescription')} actionLabel={t('users.create')} onAction={() => { setEditing(null); setDialogOpen(true) }} />}
      />

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) setEditing(null); setDialogOpen(open) }}>
        <DialogContent className="max-w-lg" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('users.edit') : t('users.create')}</DialogTitle>
          </DialogHeader>
          <UserForm
            user={editing}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('users.deleteTitle')}
        description={
          bulkDeleting.length > 0
            ? t('users.bulkDeleteConfirm', { count: bulkDeleting.length })
            : t('users.deleteConfirm', { name: deleting?.email })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
