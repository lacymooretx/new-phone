import type { ColumnDef } from "@tanstack/react-table"
import type { OutboundRoute } from "@/api/outbound-routes"
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
import i18next from "i18next"

interface ColumnActions {
  onEdit: (route: OutboundRoute) => void
  onDuplicate?: (route: OutboundRoute) => void
  onDelete: (route: OutboundRoute) => void
}

export function getOutboundRouteColumns({ onEdit, onDuplicate, onDelete }: ColumnActions): ColumnDef<OutboundRoute, unknown>[] {
  return [
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('outboundRoutes.col.name')} />,
    },
    {
      accessorKey: "dial_pattern",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('outboundRoutes.col.dialPattern', { defaultValue: 'Dial Pattern' })} />,
    },
    {
      accessorKey: "priority",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('outboundRoutes.col.priority')} />,
    },
    {
      accessorKey: "cid_mode",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('outboundRoutes.col.cidMode', { defaultValue: 'CID Mode' })} />,
      cell: ({ row }) => <Badge variant="outline">{row.original.cid_mode}</Badge>,
    },
    {
      accessorKey: "enabled",
      header: i18next.t('common.enabled'),
      cell: ({ row }) => <StatusBadge active={row.original.enabled} />,
    },
    {
      accessorKey: "is_active",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('outboundRoutes.col.status')} />,
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
