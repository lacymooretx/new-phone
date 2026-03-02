import type { ColumnDef } from "@tanstack/react-table"
import type { PortRequest, PortRequestStatus } from "@/api/port-requests"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { MoreHorizontal, Eye } from "lucide-react"
import i18next from "i18next"

interface ColumnActions {
  onView: (pr: PortRequest) => void
}

const statusConfig: Record<PortRequestStatus, { label: string; variant: "default" | "secondary" | "outline" | "destructive" }> = {
  submitted: { label: "Submitted", variant: "default" },
  pending_loa: { label: "Pending LOA", variant: "secondary" },
  loa_submitted: { label: "LOA Submitted", variant: "secondary" },
  foc_received: { label: "FOC Received", variant: "default" },
  in_progress: { label: "In Progress", variant: "default" },
  completed: { label: "Completed", variant: "default" },
  rejected: { label: "Rejected", variant: "destructive" },
  cancelled: { label: "Cancelled", variant: "outline" },
}

export function getPortRequestColumns({ onView }: ColumnActions): ColumnDef<PortRequest, unknown>[] {
  return [
    {
      accessorKey: "numbers",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t("portRequests.col.numbers")} />,
      cell: ({ row }) => {
        const numbers = row.original.numbers
        if (numbers.length <= 2) return <span className="font-mono text-xs">{numbers.join(", ")}</span>
        return (
          <span className="font-mono text-xs">
            {numbers[0]}, +{numbers.length - 1} more
          </span>
        )
      },
    },
    {
      accessorKey: "current_carrier",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t("portRequests.col.carrier")} />,
    },
    {
      accessorKey: "provider",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t("portRequests.col.provider")} />,
      cell: ({ row }) => {
        const p = row.original.provider?.toLowerCase()
        return (
          <Badge variant={p === "clearlyip" ? "default" : p === "twilio" ? "secondary" : "outline"}>
            {p === "clearlyip" ? "ClearlyIP" : p === "twilio" ? "Twilio" : row.original.provider}
          </Badge>
        )
      },
    },
    {
      accessorKey: "status",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t("portRequests.col.status")} />,
      cell: ({ row }) => {
        const cfg = statusConfig[row.original.status] ?? { label: row.original.status, variant: "outline" as const }
        return <Badge variant={cfg.variant}>{cfg.label}</Badge>
      },
      filterFn: (row, _id, filterValue: string[]) => {
        if (!filterValue?.length) return true
        return filterValue.includes(row.original.status)
      },
    },
    {
      accessorKey: "foc_date",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t("portRequests.col.focDate")} />,
      cell: ({ row }) => row.original.foc_date
        ? new Date(row.original.foc_date).toLocaleDateString()
        : <span className="text-muted-foreground">—</span>,
    },
    {
      accessorKey: "created_at",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t("portRequests.col.created")} />,
      cell: ({ row }) => new Date(row.original.created_at).toLocaleDateString(),
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0" aria-label={i18next.t("common.actions")}>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onView(row.original)}>
              <Eye className="mr-2 h-4 w-4" /> {i18next.t("portRequests.viewAction")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]
}
