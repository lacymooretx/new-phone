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

interface WfmShift {
  id: string
  name: string
  start_time: string
  end_time: string
}

interface BulkFormState {
  extensionIds: string
  shiftId: string
  dateFrom: string
  dateTo: string
}

interface ScheduleBulkDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  bulkForm: BulkFormState
  onBulkFormChange: (updater: (prev: BulkFormState) => BulkFormState) => void
  shifts: WfmShift[] | undefined
  onSubmit: () => void
  isSaving: boolean
}

export function ScheduleBulkDialog({
  open,
  onOpenChange,
  bulkForm,
  onBulkFormChange,
  shifts,
  onSubmit,
  isSaving,
}: ScheduleBulkDialogProps) {
  const { t } = useTranslation()

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle>{t("wfm.schedule.bulkAssign", "Bulk Assign")}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label>{t("wfm.schedule.extensionIds", "Extension IDs (comma-separated)")}</Label>
            <Textarea
              value={bulkForm.extensionIds}
              onChange={(e) =>
                onBulkFormChange((f) => ({ ...f, extensionIds: e.target.value }))
              }
              placeholder="ext-id-1, ext-id-2, ext-id-3"
              rows={2}
            />
          </div>
          <div className="space-y-2">
            <Label>{t("wfm.schedule.shift", "Shift")}</Label>
            <Select
              value={bulkForm.shiftId}
              onValueChange={(v) => onBulkFormChange((f) => ({ ...f, shiftId: v }))}
            >
              <SelectTrigger>
                <SelectValue placeholder={t("wfm.schedule.selectShift", "Select shift...")} />
              </SelectTrigger>
              <SelectContent>
                {shifts?.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.name} ({s.start_time} - {s.end_time})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>{t("wfm.schedule.dateFrom", "From")}</Label>
              <Input
                type="date"
                value={bulkForm.dateFrom}
                onChange={(e) =>
                  onBulkFormChange((f) => ({ ...f, dateFrom: e.target.value }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label>{t("wfm.schedule.dateTo", "To")}</Label>
              <Input
                type="date"
                value={bulkForm.dateTo}
                onChange={(e) =>
                  onBulkFormChange((f) => ({ ...f, dateTo: e.target.value }))
                }
              />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("common.cancel", "Cancel")}
          </Button>
          <Button onClick={onSubmit} disabled={isSaving}>
            {t("wfm.schedule.bulkCreate", "Create Entries")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
