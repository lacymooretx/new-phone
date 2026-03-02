import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useHolidayCalendars, useCreateHolidayCalendar, useUpdateHolidayCalendar, useDeleteHolidayCalendar, type HolidayCalendar, type HolidayCalendarCreate } from "@/api/holiday-calendars"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getHolidayCalendarColumns } from "./holiday-calendar-columns"
import { HolidayCalendarForm } from "./holiday-calendar-form"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, Calendar } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

export function HolidayCalendarsPage() {
  const { t } = useTranslation()
  const { data: calendars, isLoading, isError, error } = useHolidayCalendars()
  const createMutation = useCreateHolidayCalendar()
  const updateMutation = useUpdateHolidayCalendar()
  const deleteMutation = useDeleteHolidayCalendar()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<HolidayCalendar | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<HolidayCalendar | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<HolidayCalendar[]>([])

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: HolidayCalendarCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('holidayCalendars.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: HolidayCalendarCreate) => {
    if (!editing) return
    updateMutation.mutate({ id: editing.id, ...data }, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('holidayCalendars.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (cal: HolidayCalendar) => {
    setDeleting(cal)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: HolidayCalendar[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: HolidayCalendar[]) => {
    exportToCsv(data, [
      { key: "name", label: t('holidayCalendars.col.name') },
      { key: "description", label: t('common.description') },
      { key: "is_active", label: t('common.active') },
    ], "holiday-calendars")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t('toast.bulkDeleted', { count: bulkDeleting.length, item: t('holidayCalendars.title') }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('holidayCalendars.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getHolidayCalendarColumns({
    onEdit: (cal) => { setEditing(cal); setDialogOpen(true) },
    onDelete: handleDelete,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('holidayCalendars.title')} description={t('holidayCalendars.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('holidayCalendars.title') }]}>
        <Button onClick={() => { setEditing(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('holidayCalendars.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        searchPlaceholder={t('holidayCalendars.searchPlaceholder')}
        data={calendars ?? []}
        isLoading={isLoading}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={<EmptyState icon={Calendar} title={t('holidayCalendars.emptyTitle')} description={t('holidayCalendars.emptyDescription')} actionLabel={t('holidayCalendars.create')} onAction={() => { setEditing(null); setDialogOpen(true) }} />}
      />

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-3xl" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('holidayCalendars.edit') : t('holidayCalendars.create')}</DialogTitle>
          </DialogHeader>
          <HolidayCalendarForm
            holidayCalendar={editing}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('holidayCalendars.deleteTitle')}
        description={
          bulkDeleting.length > 0
            ? t('holidayCalendars.bulkDeleteConfirm', { count: bulkDeleting.length })
            : t('holidayCalendars.deleteConfirm', { name: deleting?.name })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
