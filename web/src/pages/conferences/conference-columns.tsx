import type { ColumnDef } from "@tanstack/react-table"
import i18next from "i18next"
import type { ConferenceBridge } from "@/api/conferences"
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
  onEdit: (conf: ConferenceBridge) => void
  onDuplicate?: (conf: ConferenceBridge) => void
  onDelete: (conf: ConferenceBridge) => void
}

export function getConferenceColumns({ onEdit, onDuplicate, onDelete }: ColumnActions): ColumnDef<ConferenceBridge, unknown>[] {
  return [
    {
      accessorKey: "room_number",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('conferences.col.roomNumber')} />,
    },
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('conferences.col.name')} />,
    },
    {
      accessorKey: "max_participants",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('conferences.col.maxMembers')} />,
    },
    {
      accessorKey: "wait_for_moderator",
      header: "Wait for Moderator",
      cell: ({ row }) =>
        row.original.wait_for_moderator ? <Badge variant="outline">Yes</Badge> : <Badge variant="secondary">No</Badge>,
    },
    {
      accessorKey: "record_conference",
      header: "Recording",
      cell: ({ row }) =>
        row.original.record_conference ? <Badge variant="outline">Yes</Badge> : <Badge variant="secondary">No</Badge>,
    },
    {
      accessorKey: "enabled",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('conferences.col.status')} />,
      cell: ({ row }) => <StatusBadge active={row.original.enabled} activeLabel="Enabled" inactiveLabel="Disabled" />,
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0" aria-label="Actions">
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
