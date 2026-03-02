import type { ColumnDef } from "@tanstack/react-table"
import type { Recording } from "@/api/recordings"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { Badge } from "@/components/ui/badge"
import i18next from "i18next"

export const recordingColumns: ColumnDef<Recording, unknown>[] = [
  {
    accessorKey: "created_at",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('recordings.col.date')} />,
    cell: ({ row }) => new Date(row.original.created_at).toLocaleString(),
  },
  {
    accessorKey: "call_id",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('recordings.col.callId', { defaultValue: 'Call ID' })} />,
    cell: ({ row }) => <span className="font-mono text-xs">{row.original.call_id.slice(0, 12)}...</span>,
  },
  {
    accessorKey: "duration_seconds",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('recordings.col.duration')} />,
    cell: ({ row }) => {
      const s = row.original.duration_seconds
      return `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`
    },
  },
  {
    accessorKey: "format",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('recordings.col.format', { defaultValue: 'Format' })} />,
    cell: ({ row }) => <Badge variant="outline">{row.original.format}</Badge>,
  },
  {
    accessorKey: "file_size_bytes",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('recordings.col.size')} />,
    cell: ({ row }) => {
      const kb = row.original.file_size_bytes / 1024
      return kb > 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb.toFixed(0)} KB`
    },
  },
  {
    accessorKey: "recording_policy",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('recordings.col.policy', { defaultValue: 'Policy' })} />,
    cell: ({ row }) => <Badge variant="secondary">{row.original.recording_policy}</Badge>,
  },
]
