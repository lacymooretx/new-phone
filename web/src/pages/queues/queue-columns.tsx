import type { ColumnDef } from "@tanstack/react-table"
import i18next from "i18next"
import type { Queue } from "@/api/queues"
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
  onEdit: (queue: Queue) => void
  onDuplicate?: (queue: Queue) => void
  onDelete: (queue: Queue) => void
}

export function getQueueColumns({ onEdit, onDuplicate, onDelete }: ColumnActions): ColumnDef<Queue, unknown>[] {
  return [
    {
      accessorKey: "queue_number",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('queues.col.number')} />,
    },
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('queues.col.name')} />,
    },
    {
      accessorKey: "strategy",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('queues.col.strategy')} />,
      cell: ({ row }) => <Badge variant="outline">{row.original.strategy}</Badge>,
    },
    {
      accessorKey: "enabled",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('queues.col.status')} />,
      cell: ({ row }) => <StatusBadge active={row.original.enabled} activeLabel="Enabled" inactiveLabel="Disabled" />,
    },
    {
      id: "members",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('queues.col.members')} />,
      cell: ({ row }) => row.original.members.length,
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
