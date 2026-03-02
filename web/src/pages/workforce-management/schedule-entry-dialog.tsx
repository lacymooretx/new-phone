import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  type WfmScheduleEntry,
  type WfmScheduleEntryCreate,
} from "@/api/workforce-management"

interface WfmShift {
  id: string
  name: string
  start_time: string
  end_time: string
  color?: string | null
}

interface ScheduleEntryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  editingEntry: WfmScheduleEntry | null
  entryForm: WfmScheduleEntryCreate
  onEntryFormChange: (updater: (prev: WfmScheduleEntryCreate) => WfmScheduleEntryCreate) => void
  shifts: WfmShift[] | undefined
  onSubmit: () => void
  isSaving: boolean
}

export function ScheduleEntryDialog({
  open,
  onOpenChange,
  editingEntry,
  entryForm,
  onEntryFormChange,
  shifts,
  onSubmit,
  isSaving,
}: ScheduleEntryDialogProps) {
  const { t } = useTranslation()

  return (
    <Dialog
      open={open}
      onOpenChange={(isOpen) => {
        onOpenChange(isOpen)
      }}
    >
      <DialogContent onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle>
            {editingEntry
              ? t("wfm.schedule.editEntry", "Edit Schedule Entry")
              : t("wfm.schedule.createEntry", "Add Entry")}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label>{t("wfm.schedule.extensionId", "Extension ID")}</Label>
            <Input
              value={entryForm.extension_id}
              onChange={(e) =>
                onEntryFormChange((f) => ({ ...f, extension_id: e.target.value }))
              }
              placeholder="ext-uuid..."
              disabled={!!editingEntry}
            />
          </div>
          <div className="space-y-2">
            <Label>{t("wfm.schedule.shift", "Shift")}</Label>
            <Select
              value={entryForm.shift_id}
              onValueChange={(v) => onEntryFormChange((f) => ({ ...f, shift_id: v }))}
            >
              <SelectTrigger>
                <SelectValue placeholder={t("wfm.schedule.selectShift", "Select shift...")} />
              </SelectTrigger>
              <SelectContent>
                {shifts?.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    <div className="flex items-center gap-2">
                      {s.color && (
                        <div
                          className="h-3 w-3 rounded-full"
                          style={{ backgroundColor: s.color }}
                        />
                      )}
                      {s.name} ({s.start_time} - {s.end_time})
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>{t("wfm.schedule.date", "Date")}</Label>
            <Input
              type="date"
              value={entryForm.date}
              onChange={(e) =>
                onEntryFormChange((f) => ({ ...f, date: e.target.value }))
              }
            />
          </div>
          <div className="space-y-2">
            <Label>{t("wfm.schedule.notes", "Notes")}</Label>
            <Textarea
              value={entryForm.notes ?? ""}
              onChange={(e) =>
                onEntryFormChange((f) => ({ ...f, notes: e.target.value || null }))
              }
              placeholder={t("wfm.schedule.notesPlaceholder", "Optional notes...")}
              rows={2}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("common.cancel", "Cancel")}
          </Button>
          <Button onClick={onSubmit} disabled={isSaving}>
            {editingEntry ? t("common.save", "Save") : t("wfm.schedule.createEntry", "Add Entry")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
