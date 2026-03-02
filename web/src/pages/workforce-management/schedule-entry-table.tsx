import { useTranslation } from "react-i18next"
import { Pencil, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { type WfmScheduleEntry } from "@/api/workforce-management"

interface ScheduleEntryTableProps {
  entries: WfmScheduleEntry[]
  shiftMap: Map<string, string>
  onEdit: (entry: WfmScheduleEntry) => void
  onDelete: (entry: WfmScheduleEntry) => void
}

export function ScheduleEntryTable({
  entries,
  shiftMap,
  onEdit,
  onDelete,
}: ScheduleEntryTableProps) {
  const { t } = useTranslation()

  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("wfm.schedule.agent", "Agent")}</TableHead>
            <TableHead>{t("wfm.schedule.date", "Date")}</TableHead>
            <TableHead>{t("wfm.schedule.shift", "Shift")}</TableHead>
            <TableHead>{t("wfm.schedule.notes", "Notes")}</TableHead>
            <TableHead className="w-24" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map((entry) => (
            <TableRow key={entry.id}>
              <TableCell className="font-medium">
                {entry.extension_name || entry.extension_number}
              </TableCell>
              <TableCell>{entry.date}</TableCell>
              <TableCell>
                {entry.shift ? (
                  <div className="flex items-center gap-2">
                    {entry.shift.color && (
                      <div
                        className="h-3 w-3 rounded-full"
                        style={{ backgroundColor: entry.shift.color }}
                      />
                    )}
                    {entry.shift.name}
                  </div>
                ) : (
                  <span className="text-muted-foreground">
                    {shiftMap.get(entry.shift_id) ?? entry.shift_id}
                  </span>
                )}
              </TableCell>
              <TableCell className="max-w-[200px] truncate text-muted-foreground">
                {entry.notes || "-"}
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onEdit(entry)}
                    title={t("common.edit", "Edit")}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onDelete(entry)}
                    title={t("common.delete", "Delete")}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
