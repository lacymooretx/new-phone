import type { ColumnDef } from "@tanstack/react-table"
import type { DID } from "@/api/dids"
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
import i18next from "i18next"

interface ColumnActions {
  onEdit: (did: DID) => void
  onDelete: (did: DID) => void
}

const statusVariant: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  active: "default",
  porting: "secondary",
  reserved: "outline",
  released: "destructive",
}

export function getDidColumns({ onEdit, onDelete }: ColumnActions): ColumnDef<DID, unknown>[] {
  return [
    {
      accessorKey: "number",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('dids.col.number')} />,
    },
    {
      accessorKey: "provider",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('dids.col.provider', { defaultValue: 'Provider' })} />,
      cell: ({ row }) => <Badge variant="outline">{row.original.provider}</Badge>,
    },
    {
      accessorKey: "status",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('dids.col.didStatus', { defaultValue: 'DID Status' })} />,
      cell: ({ row }) => (
        <Badge variant={statusVariant[row.original.status] ?? "outline"}>
          {row.original.status}
        </Badge>
      ),
    },
    {
      accessorKey: "is_emergency",
      header: i18next.t('dids.col.emergency', { defaultValue: 'Emergency' }),
      cell: ({ row }) =>
        row.original.is_emergency ? <Badge variant="destructive">E911</Badge> : <span>—</span>,
    },
    {
      accessorKey: "is_active",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('dids.col.status')} />,
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
