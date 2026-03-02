import type { ColumnDef } from "@tanstack/react-table"
import type { CDR } from "@/api/cdrs"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { Badge } from "@/components/ui/badge"
import { Disc3 } from "lucide-react"
import i18next from "i18next"

export const cdrColumns: ColumnDef<CDR, unknown>[] = [
  {
    accessorKey: "start_time",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('cdrs.col.time', { defaultValue: 'Time' })} />,
    cell: ({ row }) => new Date(row.original.start_time).toLocaleString(),
  },
  {
    accessorKey: "direction",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('cdrs.col.direction')} />,
    cell: ({ row }) => <Badge variant="outline">{row.original.direction}</Badge>,
  },
  {
    accessorKey: "caller_number",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('cdrs.col.caller', { defaultValue: 'Caller' })} />,
    cell: ({ row }) => (
      <div>
        <div>{row.original.caller_number}</div>
        {row.original.caller_name && (
          <div className="text-xs text-muted-foreground">{row.original.caller_name}</div>
        )}
      </div>
    ),
  },
  {
    accessorKey: "called_number",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('cdrs.col.called', { defaultValue: 'Called' })} />,
  },
  {
    accessorKey: "disposition",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('cdrs.col.status')} />,
    cell: ({ row }) => {
      const d = row.original.disposition
      const variant = d === "answered" ? "default" : d === "busy" ? "destructive" : "secondary"
      return <Badge variant={variant}>{d}</Badge>
    },
  },
  {
    accessorKey: "agent_disposition_label",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('cdrs.col.agentDisposition', { defaultValue: 'Agent Disposition' })} />,
    cell: ({ row }) => {
      const label = row.original.agent_disposition_label
      return label ? <Badge variant="outline">{label}</Badge> : <span className="text-muted-foreground">-</span>
    },
  },
  {
    accessorKey: "duration_seconds",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('cdrs.col.duration')} />,
    cell: ({ row }) => {
      const s = row.original.duration_seconds
      const m = Math.floor(s / 60)
      const sec = s % 60
      return `${m}:${sec.toString().padStart(2, "0")}`
    },
  },
  {
    accessorKey: "compliance_score",
    header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('cdrs.col.complianceScore', { defaultValue: 'Compliance' })} />,
    cell: ({ row }) => {
      const score = row.original.compliance_score
      if (score == null) return <span className="text-muted-foreground">-</span>
      const variant = score >= 80 ? "default" : score >= 60 ? "secondary" : "destructive"
      return <Badge variant={variant}>{score.toFixed(0)}%</Badge>
    },
  },
  {
    accessorKey: "has_recording",
    header: "",
    cell: ({ row }) => row.original.has_recording ? <Disc3 className="h-4 w-4 text-muted-foreground" /> : null,
  },
]
