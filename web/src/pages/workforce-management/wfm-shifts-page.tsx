import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Plus, Pencil, Trash2, Clock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { PageHeader } from "@/components/shared/page-header"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { EmptyState } from "@/components/shared/empty-state"
import {
  useWfmShifts,
  useCreateWfmShift,
  useUpdateWfmShift,
  useDeleteWfmShift,
  type WfmShift,
  type WfmShiftCreate,
} from "@/api/workforce-management"

const EMPTY_FORM: WfmShiftCreate = {
  name: "",
  start_time: "09:00",
  end_time: "17:00",
  break_minutes: 30,
  color: "#3b82f6",
}

export function WfmShiftsPage() {
  const { t } = useTranslation()
  const { data: shifts, isLoading, isError, error } = useWfmShifts()
  const createShift = useCreateWfmShift()
  const updateShift = useUpdateWfmShift()
  const deleteShift = useDeleteWfmShift()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<WfmShift | null>(null)
  const [form, setForm] = useState<WfmShiftCreate>(EMPTY_FORM)

  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deactivateTarget, setDeactivateTarget] = useState<WfmShift | null>(null)

  const openCreate = () => {
    setEditing(null)
    setForm(EMPTY_FORM)
    setDialogOpen(true)
  }

  const openEdit = (shift: WfmShift) => {
    setEditing(shift)
    setForm({
      name: shift.name,
      start_time: shift.start_time,
      end_time: shift.end_time,
      break_minutes: shift.break_minutes,
      color: shift.color ?? "#3b82f6",
    })
    setDialogOpen(true)
  }

  const handleSubmit = () => {
    if (!form.name.trim()) {
      toast.error(t("wfm.shifts.nameRequired", "Shift name is required"))
      return
    }

    if (editing) {
      updateShift.mutate(
        { id: editing.id, ...form },
        {
          onSuccess: () => {
            setDialogOpen(false)
            setEditing(null)
            toast.success(t("wfm.shifts.updated", "Shift updated"))
          },
          onError: (err) => toast.error(err.message),
        }
      )
    } else {
      createShift.mutate(form, {
        onSuccess: () => {
          setDialogOpen(false)
          toast.success(t("wfm.shifts.created", "Shift created"))
        },
        onError: (err) => toast.error(err.message),
      })
    }
  }

  const handleDeactivate = () => {
    if (!deactivateTarget) return
    deleteShift.mutate(deactivateTarget.id, {
      onSuccess: () => {
        setConfirmOpen(false)
        setDeactivateTarget(null)
        toast.success(t("wfm.shifts.deactivated", "Shift deactivated"))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader title={t("wfm.shifts.title", "Shifts")} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Workforce", href: "/wfm/shifts" }, { label: t("wfm.shifts.title", "Shifts") }]}>
        <Button onClick={openCreate}>
          <Plus className="mr-2 h-4 w-4" />
          {t("wfm.shifts.create", "Create Shift")}
        </Button>
      </PageHeader>

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

      {!isLoading && (!shifts || shifts.length === 0) && (
        <EmptyState
          icon={Clock}
          title={t("wfm.shifts.emptyTitle", "No shifts defined")}
          description={t("wfm.shifts.emptyDescription", "Create your first shift to start building schedules.")}
          actionLabel={t("wfm.shifts.create", "Create Shift")}
          onAction={openCreate}
        />
      )}

      {shifts && shifts.length > 0 && (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("wfm.shifts.name", "Name")}</TableHead>
                <TableHead>{t("wfm.shifts.startTime", "Start Time")}</TableHead>
                <TableHead>{t("wfm.shifts.endTime", "End Time")}</TableHead>
                <TableHead>{t("wfm.shifts.break", "Break (min)")}</TableHead>
                <TableHead>{t("wfm.shifts.color", "Color")}</TableHead>
                <TableHead>{t("wfm.shifts.status", "Status")}</TableHead>
                <TableHead className="w-24" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {shifts.map((shift) => (
                <TableRow key={shift.id}>
                  <TableCell className="font-medium">{shift.name}</TableCell>
                  <TableCell>{shift.start_time}</TableCell>
                  <TableCell>{shift.end_time}</TableCell>
                  <TableCell>{shift.break_minutes}</TableCell>
                  <TableCell>
                    {shift.color ? (
                      <div className="flex items-center gap-2">
                        <div
                          className="h-4 w-4 rounded border"
                          style={{ backgroundColor: shift.color }}
                        />
                        <span className="text-xs text-muted-foreground font-mono">
                          {shift.color}
                        </span>
                      </div>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={shift.is_active ? "default" : "secondary"}>
                      {shift.is_active
                        ? t("wfm.shifts.active", "Active")
                        : t("wfm.shifts.inactive", "Inactive")}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openEdit(shift)}
                        title={t("common.edit", "Edit")}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      {shift.is_active && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setDeactivateTarget(shift)
                            setConfirmOpen(true)
                          }}
                          title={t("wfm.shifts.deactivate", "Deactivate")}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Create / Edit Dialog */}
      <Dialog
        open={dialogOpen}
        onOpenChange={(open) => {
          if (!open) setEditing(null)
          setDialogOpen(open)
        }}
      >
        <DialogContent onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>
              {editing
                ? t("wfm.shifts.editTitle", "Edit Shift")
                : t("wfm.shifts.createTitle", "Create Shift")}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>{t("wfm.shifts.name", "Name")}</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="Morning, Evening, Night..."
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>{t("wfm.shifts.startTime", "Start Time")}</Label>
                <Input
                  type="time"
                  value={form.start_time}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, start_time: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>{t("wfm.shifts.endTime", "End Time")}</Label>
                <Input
                  type="time"
                  value={form.end_time}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, end_time: e.target.value }))
                  }
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>{t("wfm.shifts.break", "Break (min)")}</Label>
                <Input
                  type="number"
                  min={0}
                  value={form.break_minutes ?? 0}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      break_minutes: parseInt(e.target.value, 10) || 0,
                    }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>{t("wfm.shifts.color", "Color")}</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="color"
                    value={form.color ?? "#3b82f6"}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, color: e.target.value }))
                    }
                    className="h-9 w-12 p-1 cursor-pointer"
                  />
                  <Input
                    value={form.color ?? ""}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, color: e.target.value }))
                    }
                    placeholder="#3b82f6"
                    className="flex-1 font-mono text-sm"
                  />
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={createShift.isPending || updateShift.isPending}
            >
              {editing
                ? t("common.save", "Save")
                : t("wfm.shifts.create", "Create Shift")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Deactivate Confirm */}
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t("wfm.shifts.deactivateTitle", "Deactivate Shift")}
        description={t(
          "wfm.shifts.deactivateConfirm",
          `Are you sure you want to deactivate "${deactivateTarget?.name}"? It will no longer be available for scheduling.`
        )}
        confirmLabel={t("wfm.shifts.deactivate", "Deactivate")}
        variant="destructive"
        onConfirm={handleDeactivate}
      />
    </div>
  )
}
