import type { ColumnDef } from "@tanstack/react-table"
import i18next from "i18next"
import type { CallerIdRule } from "@/api/caller-id-rules"
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

interface ColumnActions {
  onEdit: (rule: CallerIdRule) => void
  onDelete: (rule: CallerIdRule) => void
}

export function getCallerIdRuleColumns({ onEdit, onDelete }: ColumnActions): ColumnDef<CallerIdRule, unknown>[] {
  return [
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('callerIdRules.col.name')} />,
    },
    {
      accessorKey: "rule_type",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('common.type')} />,
      cell: ({ row }) => (
        <Badge variant={row.original.rule_type === "block" ? "destructive" : "default"}>
          {row.original.rule_type}
        </Badge>
      ),
    },
    {
      accessorKey: "match_pattern",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('callerIdRules.col.matchPattern')} />,
    },
    {
      accessorKey: "action",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('common.actions')} />,
      cell: ({ row }) => <Badge variant="outline">{row.original.action}</Badge>,
    },
    {
      accessorKey: "priority",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('callerIdRules.col.priority')} />,
    },
    {
      accessorKey: "is_active",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('callerIdRules.col.status')} />,
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
