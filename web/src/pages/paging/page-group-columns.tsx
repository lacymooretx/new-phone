import type { ColumnDef } from "@tanstack/react-table"
import i18next from "i18next"
import type { PageGroup } from "@/api/page-groups"
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
import { MoreHorizontal, Pencil, Trash2 } from "lucide-react"

interface ColumnActions {
  onEdit: (pg: PageGroup) => void
  onDelete: (pg: PageGroup) => void
}

export function getPageGroupColumns({ onEdit, onDelete }: ColumnActions): ColumnDef<PageGroup, unknown>[] {
  return [
    {
      accessorKey: "page_number",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('paging.col.number')} />,
    },
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('paging.col.name')} />,
    },
    {
      accessorKey: "page_mode",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('common.type')} />,
      cell: ({ row }) => <Badge variant="outline">{row.original.page_mode}</Badge>,
    },
    {
      accessorKey: "timeout",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('ivrMenus.form.timeout')} />,
      cell: ({ row }) => `${row.original.timeout}s`,
    },
    {
      id: "members",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('paging.col.members')} />,
      cell: ({ row }) => row.original.members.length,
    },
    {
      accessorKey: "is_active",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('paging.col.status')} />,
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
            <DropdownMenuItem onClick={() => onDelete(row.original)} className="text-destructive">
              <Trash2 className="mr-2 h-4 w-4" /> {i18next.t('common.delete')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]
}
