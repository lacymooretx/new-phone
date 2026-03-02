import type { ColumnDef } from "@tanstack/react-table"
import i18next from "i18next"
import type { AuditLog } from "@/api/audit-logs"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { Badge } from "@/components/ui/badge"

export const auditLogColumns: ColumnDef<AuditLog, unknown>[] = [
  {
    accessorKey: "created_at",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('auditLogs.col.timestamp')} />,
    cell: ({ row }) => new Date(row.original.created_at).toLocaleString(),
  },
  {
    accessorKey: "action",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('auditLogs.col.action')} />,
    cell: ({ row }) => <Badge variant="outline">{row.original.action}</Badge>,
  },
  {
    accessorKey: "resource_type",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('auditLogs.col.resource')} />,
  },
  {
    accessorKey: "resource_id",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('auditLogs.col.details')} />,
    cell: ({ row }) => {
      const id = row.original.resource_id
      if (!id) return "—"
      return id.length > 12 ? `${id.slice(0, 12)}...` : id
    },
  },
  {
    accessorKey: "ip_address",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('auditLogs.col.ipAddress')} />,
    cell: ({ row }) => row.original.ip_address || "—",
  },
  {
    accessorKey: "user_agent",
    header: i18next.t('auditLogs.col.user', { defaultValue: 'User Agent' }),
    cell: ({ row }) => {
      const ua = row.original.user_agent
      if (!ua) return "—"
      return ua.length > 40 ? `${ua.slice(0, 40)}...` : ua
    },
  },
]
