import type { ColumnDef } from "@tanstack/react-table"
import i18next from "i18next"
import type { IVRMenu } from "@/api/ivr-menus"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { StatusBadge } from "@/components/shared/status-badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { MoreHorizontal, Pencil, Trash2, Copy } from "lucide-react"

interface ColumnActions {
  onEdit: (menu: IVRMenu) => void
  onDuplicate?: (menu: IVRMenu) => void
  onDelete: (menu: IVRMenu) => void
}

export function getIvrMenuColumns({ onEdit, onDuplicate, onDelete }: ColumnActions): ColumnDef<IVRMenu, unknown>[] {
  return [
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('ivrMenus.col.name')} />,
    },
    {
      accessorKey: "description",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('ivrMenus.col.description')} />,
      cell: ({ row }) => row.original.description || "—",
    },
    {
      accessorKey: "timeout",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('ivrMenus.form.timeout')} />,
      cell: ({ row }) => `${row.original.timeout}s`,
    },
    {
      accessorKey: "max_failures",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('ivrMenus.form.maxFailures')} />,
    },
    {
      accessorKey: "enabled",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('ivrMenus.col.status')} />,
      cell: ({ row }) => <StatusBadge active={row.original.enabled} activeLabel="Enabled" inactiveLabel="Disabled" />,
    },
    {
      id: "options",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('ivrMenus.col.options')} />,
      cell: ({ row }) => row.original.options.length,
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
