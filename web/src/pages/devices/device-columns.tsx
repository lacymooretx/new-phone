import type { ColumnDef } from "@tanstack/react-table"
import i18next from "i18next"
import type { Device } from "@/api/devices"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { MoreHorizontal, Pencil, Trash2, Keyboard, Copy } from "lucide-react"

interface ColumnActions {
  onEdit: (device: Device) => void
  onDelete: (device: Device) => void
  onEditKeys: (device: Device) => void
  onCopyProvUrl: (device: Device) => void
}

function formatMac(mac: string): string {
  if (mac.length !== 12) return mac
  return mac.replace(/(.{2})/g, "$1:").slice(0, -1).toUpperCase()
}

function formatProvisionedAt(dt: string | null): string {
  if (!dt) return "Never"
  const d = new Date(dt)
  return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

export function getDeviceColumns({ onEdit, onDelete, onEditKeys, onCopyProvUrl }: ColumnActions): ColumnDef<Device>[] {
  return [
    {
      accessorKey: "mac_address",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('devices.col.macAddress')} />,
      cell: ({ row }) => <span className="font-mono text-xs">{formatMac(row.original.mac_address)}</span>,
    },
    {
      id: "model",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('devices.col.model')} />,
      accessorFn: (row) => `${row.phone_model_manufacturer || ""} ${row.phone_model_name || ""}`.trim(),
      cell: ({ row }) => (
        <span>{row.original.phone_model_manufacturer} {row.original.phone_model_name}</span>
      ),
    },
    {
      accessorKey: "extension_number",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('devices.col.extension')} />,
      cell: ({ row }) => row.original.extension_number || "—",
    },
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('devices.col.name')} />,
      cell: ({ row }) => row.original.name || "—",
    },
    {
      accessorKey: "location",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Location" />,
      cell: ({ row }) => row.original.location || "—",
    },
    {
      accessorKey: "last_provisioned_at",
      header: ({ column }) => <DataTableColumnHeader column={column} title="Last Provisioned" />,
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground">{formatProvisionedAt(row.original.last_provisioned_at)}</span>
      ),
    },
    {
      accessorKey: "is_active",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('devices.col.status')} />,
      cell: ({ row }) => <StatusBadge active={row.original.is_active && row.original.provisioning_enabled} />,
    },
    {
      id: "actions",
      cell: function ActionsCell({ row }) {
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
              <DropdownMenuItem onClick={() => onEditKeys(row.original)}>
                <Keyboard className="mr-2 h-4 w-4" /> {i18next.t('devices.form.lineKeys')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onCopyProvUrl(row.original)}>
                <Copy className="mr-2 h-4 w-4" /> Copy Provisioning URL
              </DropdownMenuItem>
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
