import type { ColumnDef } from "@tanstack/react-table"
import i18next from "i18next"
import type { HolidayCalendar } from "@/api/holiday-calendars"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { StatusBadge } from "@/components/shared/status-badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { MoreHorizontal, Pencil, Trash2 } from "lucide-react"

interface ColumnActions {
  onEdit: (cal: HolidayCalendar) => void
  onDelete: (cal: HolidayCalendar) => void
}

export function getHolidayCalendarColumns({ onEdit, onDelete }: ColumnActions): ColumnDef<HolidayCalendar, unknown>[] {
  return [
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('holidayCalendars.col.name')} />,
    },
    {
      accessorKey: "description",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('common.description')} />,
      cell: ({ row }) => row.original.description || "—",
    },
    {
      id: "entries_count",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('holidayCalendars.col.holidays')} />,
      cell: ({ row }) => row.original.entries?.length ?? 0,
    },
    {
      accessorKey: "is_active",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('holidayCalendars.col.status')} />,
      cell: ({ row }) => <StatusBadge active={row.original.is_active} />,
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0" aria-label={i18next.t('common.actions')}>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onEdit(row.original)}>
              <Pencil className="mr-2 h-4 w-4" /> {i18next.t('common.edit')}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onDelete(row.original)} className="text-destructive">
              <Trash2 className="mr-2 h-4 w-4" /> {i18next.t('common.delete')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]
}
