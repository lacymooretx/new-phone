import type { ColumnDef } from "@tanstack/react-table"
import i18next from "i18next"
import type { TimeCondition } from "@/api/time-conditions"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { MoreHorizontal, Pencil, Trash2, Copy } from "lucide-react"

interface ColumnActions {
  onEdit: (tc: TimeCondition) => void
  onDuplicate?: (tc: TimeCondition) => void
  onDelete: (tc: TimeCondition) => void
}

export function getTimeConditionColumns({ onEdit, onDuplicate, onDelete }: ColumnActions): ColumnDef<TimeCondition, unknown>[] {
  return [
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('timeConditions.col.name')} />,
    },
    {
      accessorKey: "timezone",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('timeConditions.col.timezone')} />,
    },
    {
      accessorKey: "match_destination_type",
      header: i18next.t('timeConditions.col.matchDest'),
      cell: ({ row }) => <Badge variant="outline">{row.original.match_destination_type}</Badge>,
    },
    {
      accessorKey: "nomatch_destination_type",
      header: i18next.t('timeConditions.col.noMatchDest'),
      cell: ({ row }) => <Badge variant="outline">{row.original.nomatch_destination_type}</Badge>,
    },
    {
      accessorKey: "enabled",
      header: i18next.t('common.enabled'),
      cell: ({ row }) => <StatusBadge active={row.original.enabled} activeLabel={i18next.t('common.enabled')} inactiveLabel={i18next.t('common.disabled')} />,
    },
    {
      accessorKey: "is_active",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('timeConditions.col.status')} />,
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
            {onDuplicate && (
              <DropdownMenuItem onClick={() => onDuplicate(row.original)}>
                <Copy className="mr-2 h-4 w-4" /> {i18next.t('common.duplicate')}
              </DropdownMenuItem>
            )}
            <DropdownMenuItem onClick={() => onDelete(row.original)} className="text-destructive">
              <Trash2 className="mr-2 h-4 w-4" /> {i18next.t('common.delete')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]
}
