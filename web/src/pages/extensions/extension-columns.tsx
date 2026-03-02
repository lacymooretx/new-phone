import type { ColumnDef } from "@tanstack/react-table"
import i18next from "i18next"
import type { Extension } from "@/api/extensions"
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
import { useNavigate } from "react-router"
import { MoreHorizontal, Pencil, Trash2, PhoneForwarded, Copy } from "lucide-react"

interface ColumnActions {
  onEdit: (ext: Extension) => void
  onDuplicate?: (ext: Extension) => void
  onDelete: (ext: Extension) => void
}

export function getExtensionColumns({ onEdit, onDuplicate, onDelete }: ColumnActions): ColumnDef<Extension, unknown>[] {
  return [
    {
      accessorKey: "extension_number",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('extensions.col.extension')} />,
    },
    {
      accessorKey: "internal_cid_name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('extensions.col.name')} />,
      cell: ({ row }) => row.original.internal_cid_name || "—",
    },
    {
      accessorKey: "is_active",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('extensions.col.status')} />,
      cell: ({ row }) => <StatusBadge active={row.original.is_active} />,
    },
    {
      accessorKey: "dnd_enabled",
      header: "DND",
      cell: ({ row }) =>
        row.original.dnd_enabled ? <Badge variant="destructive">DND</Badge> : null,
    },
    {
      accessorKey: "class_of_service",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('extensions.col.cos')} />,
      cell: ({ row }) => <Badge variant="outline">{row.original.class_of_service}</Badge>,
    },
    {
      id: "actions",
      cell: function ActionsCell({ row }) {
        const navigate = useNavigate()
        return (
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
              <DropdownMenuItem onClick={() => navigate(`/extensions/${row.original.id}/follow-me`)}>
                <PhoneForwarded className="mr-2 h-4 w-4" /> {i18next.t('common.followMe')}
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
        )
      },
    },
  ]
}
