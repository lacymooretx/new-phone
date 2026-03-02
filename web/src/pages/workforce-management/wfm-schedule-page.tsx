import { useState, useMemo } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Plus, Users, Calendar } from "lucide-react"
import { Button } from "@/components/ui/button"
import { PageHeader } from "@/components/shared/page-header"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { EmptyState } from "@/components/shared/empty-state"
import {
  useWfmSchedule,
  useWfmShifts,
  useCreateWfmScheduleEntry,
  useBulkCreateWfmScheduleEntries,
  useUpdateWfmScheduleEntry,
  useDeleteWfmScheduleEntry,
  useWfmScheduleOverview,
  type WfmScheduleEntry,
  type WfmScheduleEntryCreate,
} from "@/api/workforce-management"
import { ScheduleToolbar } from "./schedule-toolbar"
import { ScheduleEntryTable } from "./schedule-entry-table"
import { ScheduleWeekSummary } from "./schedule-week-summary"
import { ScheduleEntryDialog } from "./schedule-entry-dialog"
import { ScheduleBulkDialog } from "./schedule-bulk-dialog"

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getWeekDates(weekOffset: number) {
  const now = new Date()
  const monday = new Date(now)
  monday.setDate(now.getDate() - now.getDay() + 1 + weekOffset * 7)
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  return {
    from: monday.toISOString().split("T")[0],
    to: sunday.toISOString().split("T")[0],
    label: `${monday.toLocaleDateString()} - ${sunday.toLocaleDateString()}`,
  }
}

function getDatesInRange(from: string, to: string): string[] {
  const dates: string[] = []
  const current = new Date(from + "T00:00:00")
  const end = new Date(to + "T00:00:00")
  while (current <= end) {
    dates.push(current.toISOString().split("T")[0])
    current.setDate(current.getDate() + 1)
  }
  return dates
}

const EMPTY_ENTRY: WfmScheduleEntryCreate = {
  extension_id: "",
  shift_id: "",
  date: "",
  notes: null,
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function WfmSchedulePage() {
  const { t } = useTranslation()

  // Week navigation
  const [weekOffset, setWeekOffset] = useState(0)
  const week = useMemo(() => getWeekDates(weekOffset), [weekOffset])

  // Extension filter
  const [filterExtensionId, setFilterExtensionId] = useState("")

  // Queries
  const {
    data: entries,
    isLoading,
    isError,
    error,
  } = useWfmSchedule(week.from, week.to, filterExtensionId || undefined)
  const { data: shifts } = useWfmShifts(true)
  const { data: overview } = useWfmScheduleOverview(week.from, week.to)

  // Mutations
  const createEntry = useCreateWfmScheduleEntry()
  const bulkCreate = useBulkCreateWfmScheduleEntries()
  const updateEntry = useUpdateWfmScheduleEntry()
  const deleteEntry = useDeleteWfmScheduleEntry()

  // Single entry dialog
  const [entryDialogOpen, setEntryDialogOpen] = useState(false)
  const [editingEntry, setEditingEntry] = useState<WfmScheduleEntry | null>(null)
  const [entryForm, setEntryForm] = useState<WfmScheduleEntryCreate>(EMPTY_ENTRY)

  // Bulk dialog
  const [bulkDialogOpen, setBulkDialogOpen] = useState(false)
  const [bulkForm, setBulkForm] = useState({
    extensionIds: "",
    shiftId: "",
    dateFrom: week.from,
    dateTo: week.to,
  })

  // Delete confirm
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<WfmScheduleEntry | null>(null)

  // ---- Single entry handlers ----

  const openCreateEntry = () => {
    setEditingEntry(null)
    setEntryForm({ ...EMPTY_ENTRY, date: week.from })
    setEntryDialogOpen(true)
  }

  const openEditEntry = (entry: WfmScheduleEntry) => {
    setEditingEntry(entry)
    setEntryForm({
      extension_id: entry.extension_id,
      shift_id: entry.shift_id,
      date: entry.date,
      notes: entry.notes,
    })
    setEntryDialogOpen(true)
  }

  const handleSubmitEntry = () => {
    if (!entryForm.extension_id || !entryForm.shift_id || !entryForm.date) {
      toast.error(t("wfm.schedule.requiredFields", "Extension, shift, and date are required"))
      return
    }

    if (editingEntry) {
      updateEntry.mutate(
        { id: editingEntry.id, ...entryForm },
        {
          onSuccess: () => {
            setEntryDialogOpen(false)
            setEditingEntry(null)
            toast.success(t("wfm.schedule.entryUpdated", "Schedule entry updated"))
          },
          onError: (err) => toast.error(err.message),
        }
      )
    } else {
      createEntry.mutate(entryForm, {
        onSuccess: () => {
          setEntryDialogOpen(false)
          toast.success(t("wfm.schedule.entryCreated", "Schedule entry created"))
        },
        onError: (err) => toast.error(err.message),
      })
    }
  }

  // ---- Bulk handler ----

  const handleBulkCreate = () => {
    const ids = bulkForm.extensionIds
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)

    if (ids.length === 0 || !bulkForm.shiftId || !bulkForm.dateFrom || !bulkForm.dateTo) {
      toast.error(t("wfm.schedule.bulkRequired", "Extension IDs, shift, and date range are required"))
      return
    }

    const dates = getDatesInRange(bulkForm.dateFrom, bulkForm.dateTo)
    const payload: WfmScheduleEntryCreate[] = ids.flatMap((extId) =>
      dates.map((date) => ({
        extension_id: extId,
        shift_id: bulkForm.shiftId,
        date,
      }))
    )

    bulkCreate.mutate(payload, {
      onSuccess: (created) => {
        setBulkDialogOpen(false)
        toast.success(
          t("wfm.schedule.bulkCreated", `${created.length} schedule entries created`)
        )
      },
      onError: (err) => toast.error(err.message),
    })
  }

  // ---- Delete handler ----

  const handleDelete = () => {
    if (!deleteTarget) return
    deleteEntry.mutate(deleteTarget.id, {
      onSuccess: () => {
        setConfirmOpen(false)
        setDeleteTarget(null)
        toast.success(t("wfm.schedule.entryDeleted", "Schedule entry deleted"))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  // ---- Shift name lookup ----
  const shiftMap = useMemo(() => {
    const map = new Map<string, string>()
    shifts?.forEach((s) => map.set(s.id, s.name))
    return map
  }, [shifts])

  return (
    <div className="space-y-6">
      <PageHeader title={t("wfm.schedule.title", "Schedule")} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Workforce", href: "/wfm/shifts" }, { label: t("wfm.schedule.title", "Schedule") }]}>
        <Button variant="outline" onClick={() => setBulkDialogOpen(true)}>
          <Users className="mr-2 h-4 w-4" />
          {t("wfm.schedule.bulkAssign", "Bulk Assign")}
        </Button>
        <Button onClick={openCreateEntry}>
          <Plus className="mr-2 h-4 w-4" />
          {t("wfm.schedule.createEntry", "Add Entry")}
        </Button>
      </PageHeader>

      <ScheduleToolbar
        weekLabel={week.label}
        weekOffset={weekOffset}
        onPrevWeek={() => setWeekOffset((w) => w - 1)}
        onNextWeek={() => setWeekOffset((w) => w + 1)}
        onToday={() => setWeekOffset(0)}
        filterExtensionId={filterExtensionId}
        onFilterChange={setFilterExtensionId}
      />

      {/* Error / Loading */}
      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t("common.failedToLoad", "Failed to load")}: {error?.message}
        </div>
      )}

      {isLoading && (
        <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
          {t("common.loading", "Loading...")}
        </div>
      )}

      {/* Schedule table */}
      {!isLoading && entries && entries.length === 0 && (
        <EmptyState
          icon={Calendar}
          title={t("wfm.schedule.emptyTitle", "No schedule entries")}
          description={t("wfm.schedule.emptyDescription", "Add entries or use bulk assign to populate the schedule.")}
          actionLabel={t("wfm.schedule.createEntry", "Add Entry")}
          onAction={openCreateEntry}
        />
      )}

      {!isLoading && entries && entries.length > 0 && (
        <ScheduleEntryTable
          entries={entries}
          shiftMap={shiftMap}
          onEdit={openEditEntry}
          onDelete={(entry) => {
            setDeleteTarget(entry)
            setConfirmOpen(true)
          }}
        />
      )}

      {/* Overview summary cards */}
      {overview && overview.length > 0 && (
        <ScheduleWeekSummary overview={overview} />
      )}

      {/* Create / Edit Entry Dialog */}
      <ScheduleEntryDialog
        open={entryDialogOpen}
        onOpenChange={(open) => {
          if (!open) setEditingEntry(null)
          setEntryDialogOpen(open)
        }}
        editingEntry={editingEntry}
        entryForm={entryForm}
        onEntryFormChange={setEntryForm}
        shifts={shifts}
        onSubmit={handleSubmitEntry}
        isSaving={createEntry.isPending || updateEntry.isPending}
      />

      {/* Bulk Assign Dialog */}
      <ScheduleBulkDialog
        open={bulkDialogOpen}
        onOpenChange={setBulkDialogOpen}
        bulkForm={bulkForm}
        onBulkFormChange={setBulkForm}
        shifts={shifts}
        onSubmit={handleBulkCreate}
        isSaving={bulkCreate.isPending}
      />

      {/* Delete Confirm */}
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t("wfm.schedule.deleteTitle", "Delete Schedule Entry")}
        description={t(
          "wfm.schedule.deleteConfirm",
          "Are you sure you want to delete this schedule entry? This action cannot be undone."
        )}
        confirmLabel={t("common.delete", "Delete")}
        variant="destructive"
        onConfirm={handleDelete}
      />
    </div>
  )
}
