import type { ColumnDef } from "@tanstack/react-table"
import type { SIPTrunk } from "@/api/sip-trunks"
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
  onEdit: (trunk: SIPTrunk) => void
  onDelete: (trunk: SIPTrunk) => void
}

export function getSipTrunkColumns({ onEdit, onDelete }: ColumnActions): ColumnDef<SIPTrunk, unknown>[] {
  return [
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('sipTrunks.col.name')} />,
    },
    {
      accessorKey: "host",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('sipTrunks.col.host')} />,
    },
    {
      accessorKey: "auth_type",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('sipTrunks.form.authType', { defaultValue: 'Auth Type' })} />,
      cell: ({ row }) => <Badge variant="outline">{row.original.auth_type}</Badge>,
    },
    {
      accessorKey: "transport",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('sipTrunks.form.transport')} />,
      cell: ({ row }) => <Badge variant="secondary">{row.original.transport}</Badge>,
    },
    {
      accessorKey: "max_channels",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('sipTrunks.form.maxChannels')} />,
    },
    {
      accessorKey: "inbound_cid_mode",
      header: i18next.t('sipTrunks.col.inboundCid', { defaultValue: 'Inbound CID' }),
      cell: ({ row }) => <Badge variant="outline">{row.original.inbound_cid_mode}</Badge>,
    },
    {
      accessorKey: "is_active",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('sipTrunks.col.status', { defaultValue: 'Status' })} />,
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
