import type { ColumnDef } from "@tanstack/react-table"
import i18next from "i18next"
import type { User } from "@/api/users"
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
  onEdit: (user: User) => void
  onDelete: (user: User) => void
}

export function getUserColumns({ onEdit, onDelete }: ColumnActions): ColumnDef<User, unknown>[] {
  return [
    {
      accessorKey: "email",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('users.col.email')} />,
    },
    {
      id: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('users.col.name')} />,
      accessorFn: (row) => `${row.first_name} ${row.last_name}`,
    },
    {
      accessorKey: "role",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('users.col.role')} />,
      cell: ({ row }) => (
        <Badge variant="outline">
          {i18next.t(`users.roles.${row.original.role}`, { defaultValue: row.original.role.replace(/_/g, " ") })}
        </Badge>
      ),
    },
    {
      accessorKey: "mfa_enabled",
      header: i18next.t('users.col.mfa'),
      cell: ({ row }) => (
        <Badge variant={row.original.mfa_enabled ? "default" : "secondary"}>
          {row.original.mfa_enabled ? i18next.t('common.enabled') : i18next.t('common.disabled')}
        </Badge>
      ),
    },
    {
      accessorKey: "is_active",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('users.col.status')} />,
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
