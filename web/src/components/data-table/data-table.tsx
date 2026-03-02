import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import {
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
  type VisibilityState,
  type RowSelectionState,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  useReactTable,
} from "@tanstack/react-table"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import { Skeleton } from "@/components/ui/skeleton"
import { DataTablePagination } from "./data-table-pagination"
import { Search, SlidersHorizontal, Trash2, Download } from "lucide-react"
import type { ReactNode } from "react"

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  isLoading?: boolean
  toolbar?: ReactNode
  onRowClick?: (row: TData) => void
  pageSize?: number
  searchPlaceholder?: string
  emptyState?: ReactNode
  enableRowSelection?: boolean
  onBulkDelete?: (rows: TData[]) => void
  onExport?: (data: TData[]) => void
  // Server-side pagination
  manualPagination?: boolean
  pageCount?: number
  onPaginationChange?: (pageIndex: number, pageSize: number) => void
}

export function DataTable<TData, TValue>({
  columns,
  data,
  isLoading,
  toolbar,
  onRowClick,
  pageSize = 10,
  searchPlaceholder,
  emptyState,
  enableRowSelection,
  onBulkDelete,
  onExport,
  manualPagination,
  pageCount,
  onPaginationChange,
}: DataTableProps<TData, TValue>) {
  const { t } = useTranslation()
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [globalFilter, setGlobalFilter] = useState("")
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize })

  const allColumns = useMemo<ColumnDef<TData, TValue>[]>(() => {
    if (!enableRowSelection) return columns
    const selectColumn: ColumnDef<TData, TValue> = {
      id: "select",
      header: ({ table: t }) => (
        <Checkbox
          checked={t.getIsAllPageRowsSelected() || (t.getIsSomePageRowsSelected() && "indeterminate")}
          onCheckedChange={(value) => t.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label="Select row"
          onClick={(e) => e.stopPropagation()}
        />
      ),
      enableSorting: false,
      enableHiding: false,
    }
    return [selectColumn, ...columns]
  }, [columns, enableRowSelection])

  const table = useReactTable({
    data,
    columns: allColumns,
    state: { sorting, columnFilters, globalFilter, columnVisibility, pagination, rowSelection },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    onPaginationChange: (updater) => {
      const next = typeof updater === "function" ? updater(pagination) : updater
      setPagination(next)
      if (manualPagination && onPaginationChange) {
        onPaginationChange(next.pageIndex, next.pageSize)
      }
    },
    enableRowSelection: !!enableRowSelection,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: manualPagination ? undefined : getSortedRowModel(),
    getFilteredRowModel: manualPagination ? undefined : getFilteredRowModel(),
    getPaginationRowModel: manualPagination ? undefined : getPaginationRowModel(),
    manualPagination,
    pageCount,
    globalFilterFn: "includesString",
  })

  const selectedCount = Object.keys(rowSelection).length

  if (isLoading) {
    return (
      <div className="space-y-3">
        {searchPlaceholder && !manualPagination && (
          <div className="relative max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input disabled placeholder={searchPlaceholder} className="pl-9" />
          </div>
        )}
        {toolbar}
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                {allColumns.map((_, i) => (
                  <TableHead key={i}>
                    <Skeleton className="h-4 w-24" />
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {allColumns.map((_, j) => (
                    <TableCell key={j}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    )
  }

  const toggleableColumns = table.getAllColumns().filter(
    (col) => col.getCanHide() && col.id !== "actions" && col.id !== "select"
  )

  const handleBulkDelete = () => {
    if (!onBulkDelete) return
    const selectedRows = table.getFilteredSelectedRowModel().rows.map((r) => r.original)
    onBulkDelete(selectedRows)
    setRowSelection({})
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        {searchPlaceholder && !manualPagination && (
          <div className="relative max-w-sm flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              placeholder={searchPlaceholder}
              className="pl-9"
            />
          </div>
        )}
        {toolbar}
        {selectedCount > 0 && onBulkDelete && (
          <Button variant="destructive" size="sm" onClick={handleBulkDelete}>
            <Trash2 className="mr-1 h-4 w-4" /> {t('table.deleteSelected', { count: selectedCount })}
          </Button>
        )}
        {onExport && data.length > 0 && (
          <Button variant="outline" size="sm" onClick={() => onExport(data)}>
            <Download className="mr-1 h-4 w-4" /> {t('common.exportCsv')}
          </Button>
        )}
        {toggleableColumns.length > 0 && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="ml-auto">
                <SlidersHorizontal className="mr-1 h-4 w-4" />
                {t('common.columns')}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {toggleableColumns.map((column) => (
                <DropdownMenuCheckboxItem
                  key={column.id}
                  checked={column.getIsVisible()}
                  onCheckedChange={(value) => column.toggleVisibility(!!value)}
                  className="capitalize"
                >
                  {typeof column.columnDef.header === "string"
                    ? column.columnDef.header
                    : column.id.replace(/_/g, " ")}
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                  onClick={() => onRowClick?.(row.original)}
                  className={onRowClick ? "cursor-pointer" : undefined}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={allColumns.length} className="h-24 text-center">
                  {emptyState ?? t('common.noResults')}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <DataTablePagination table={table} selectedCount={selectedCount} />
    </div>
  )
}
