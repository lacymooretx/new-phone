import type { ColumnDef } from "@tanstack/react-table"
import type { SIPTrunk } from "@/api/sip-trunks"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { MoreHorizontal, Pencil, Trash2, TestTube2, CloudOff } from "lucide-react"
import i18next from "i18next"

interface ColumnActions {
  onEdit: (trunk: SIPTrunk) => void
  onDelete: (trunk: SIPTrunk) => void
  onTest: (trunk: SIPTrunk) => void
  onDeprovision: (trunk: SIPTrunk) => void
}

const providerVariant: Record<string, "default" | "secondary" | "outline"> = {
  clearlyip: "default",
  twilio: "secondary",
}

export function getSipTrunkColumns({ onEdit, onDelete, onTest, onDeprovision }: ColumnActions): ColumnDef<SIPTrunk, unknown>[] {
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
      id: "provider_badge",
      header: i18next.t('sipTrunks.col.provider', { defaultValue: 'Provider' }),
      cell: ({ row }) => {
        const trunk = row.original
        // Detect provider from host or name pattern
        const provider = trunk.host.includes("clearlyip") ? "clearlyip"
          : trunk.host.includes("twilio") ? "twilio"
          : null
        if (!provider) return <Badge variant="outline">{i18next.t('sipTrunks.providerManual')}</Badge>
        return (
          <Badge variant={providerVariant[provider] ?? "outline"}>
            {provider === "clearlyip" ? "ClearlyIP" : "Twilio"}
          </Badge>
        )
      },
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
            <DropdownMenuItem onClick={() => onTest(row.original)}>
              <TestTube2 className="mr-2 h-4 w-4" /> {i18next.t('sipTrunks.testAction')}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onEdit(row.original)}>
              <Pencil className="mr-2 h-4 w-4" /> {i18next.t('common.edit')}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => onDeprovision(row.original)} className="text-destructive">
              <CloudOff className="mr-2 h-4 w-4" /> {i18next.t('sipTrunks.deprovisionAction')}
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
