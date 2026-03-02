import type { ColumnDef } from "@tanstack/react-table"
import i18next from "i18next"
import type { RingGroup } from "@/api/ring-groups"
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
  onEdit: (rg: RingGroup) => void
  onDuplicate?: (rg: RingGroup) => void
  onDelete: (rg: RingGroup) => void
}

export function getRingGroupColumns({ onEdit, onDuplicate, onDelete }: ColumnActions): ColumnDef<RingGroup, unknown>[] {
  return [
    {
      accessorKey: "group_number",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('ringGroups.col.number')} />,
    },
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('ringGroups.col.name')} />,
    },
    {
      accessorKey: "ring_strategy",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('ringGroups.col.strategy')} />,
      cell: ({ row }) => <Badge variant="outline">{row.original.ring_strategy}</Badge>,
    },
    {
      id: "members",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('ringGroups.col.members')} />,
      cell: ({ row }) => row.original.member_extension_ids.length,
    },
    {
      accessorKey: "is_active",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('ringGroups.col.status')} />,
      cell: ({ row }) => <StatusBadge active={row.original.is_active} />,
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
