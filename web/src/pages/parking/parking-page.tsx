import { useState } from "react"
import { useTranslation } from "react-i18next"
import {
  useParkingLots,
  useCreateParkingLot,
  useUpdateParkingLot,
  useDeleteParkingLot,
  useLotSlotStates,
  type ParkingLot,
  type ParkingLotCreate,
  type SlotState,
} from "@/api/parking"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { ParkingLotForm } from "./parking-lot-form"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { EmptyState } from "@/components/shared/empty-state"
import { StatusBadge } from "@/components/shared/status-badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Plus, ParkingSquare, LayoutGrid, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { exportToCsv } from "@/lib/export-csv"
import type { ColumnDef } from "@tanstack/react-table"
import i18next from "i18next"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { MoreHorizontal, Pencil, Trash2 } from "lucide-react"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"

function getParkingLotColumns(actions: {
  onEdit: (lot: ParkingLot) => void
  onDelete: (lot: ParkingLot) => void
}): ColumnDef<ParkingLot, unknown>[] {
  return [
    {
      accessorKey: "lot_number",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('parking.col.lotNumber')} />,
    },
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('parking.col.name')} />,
    },
    {
      id: "slots",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('parking.col.slotRange')} />,
      cell: ({ row }) => `${row.original.slot_start} - ${row.original.slot_end}`,
    },
    {
      accessorKey: "timeout_seconds",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('parking.col.timeout')} />,
      cell: ({ row }) => `${row.original.timeout_seconds}s`,
    },
    {
      accessorKey: "comeback_enabled",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('parking.col.comeback')} />,
      cell: ({ row }) => (
        <StatusBadge
          active={row.original.comeback_enabled}
          activeLabel={i18next.t('common.enabled')}
          inactiveLabel={i18next.t('common.disabled')}
        />
      ),
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0" aria-label="Actions">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => actions.onEdit(row.original)}>
              <Pencil className="mr-2 h-4 w-4" /> {i18next.t('common.edit')}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => actions.onDelete(row.original)} className="text-destructive">
              <Trash2 className="mr-2 h-4 w-4" /> {i18next.t('common.delete')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]
}

function SlotGrid({ lot }: { lot: ParkingLot }) {
  const { data: slots, isLoading } = useLotSlotStates(lot.id)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-4">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="grid grid-cols-5 gap-2">
      {(slots ?? []).map((slot: SlotState) => (
        <Tooltip key={slot.slot_number}>
          <TooltipTrigger asChild>
            <div
              className={`rounded-md border p-2 text-center text-sm font-mono cursor-default transition-colors ${
                slot.occupied
                  ? "bg-green-100 border-green-300 dark:bg-green-900/30 dark:border-green-700"
                  : "bg-muted border-muted-foreground/20"
              }`}
            >
              {slot.slot_number}
            </div>
          </TooltipTrigger>
          <TooltipContent>
            {slot.occupied ? (
              <div className="text-xs">
                <div>{slot.caller_id_name || slot.caller_id_number || "Unknown"}</div>
                {slot.caller_id_number && <div>{slot.caller_id_number}</div>}
                {slot.parked_by && <div>Parked by: {slot.parked_by}</div>}
              </div>
            ) : (
              <span>{i18next.t('parking.slotEmpty')}</span>
            )}
          </TooltipContent>
        </Tooltip>
      ))}
    </div>
  )
}

export function ParkingPage() {
  const { t } = useTranslation()
  const { data: lots, isLoading, isError, error } = useParkingLots()
  const createMutation = useCreateParkingLot()
  const updateMutation = useUpdateParkingLot()
  const deleteMutation = useDeleteParkingLot()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<ParkingLot | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<ParkingLot | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<ParkingLot[]>([])

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: ParkingLotCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('parking.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: ParkingLotCreate) => {
    if (!editing) return
    updateMutation.mutate({ id: editing.id, ...data }, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('parking.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (lot: ParkingLot) => {
    setDeleting(lot)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: ParkingLot[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: ParkingLot[]) => {
    exportToCsv(data, [
      { key: "lot_number", label: "Lot Number" },
      { key: "name", label: "Name" },
      { key: "slot_start", label: "Slot Start" },
      { key: "slot_end", label: "Slot End" },
      { key: "timeout_seconds", label: "Timeout" },
      { key: "comeback_enabled", label: "Comeback" },
    ], "parking-lots")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t('toast.bulkDeleted', { count: bulkDeleting.length, item: t('parking.title').toLowerCase() }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('parking.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getParkingLotColumns({
    onEdit: (lot) => { setEditing(lot); setDialogOpen(true) },
    onDelete: handleDelete,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('parking.title')} description={t('parking.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('parking.title') }]}>
        <Button onClick={() => { setEditing(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('parking.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <Tabs defaultValue="lots">
        <TabsList>
          <TabsTrigger value="lots">
            <ParkingSquare className="mr-2 h-4 w-4" />
            {t('parking.tab.lots')}
          </TabsTrigger>
          <TabsTrigger value="panel">
            <LayoutGrid className="mr-2 h-4 w-4" />
            {t('parking.tab.livePanel')}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="lots" className="mt-4">
          <DataTable
            columns={columns}
            data={lots ?? []}
            isLoading={isLoading}
            searchPlaceholder={t('parking.searchPlaceholder')}
            enableRowSelection
            onBulkDelete={handleBulkDelete}
            onExport={handleExport}
            emptyState={
              <EmptyState
                icon={ParkingSquare}
                title={t('parking.emptyTitle')}
                description={t('parking.emptyDescription')}
                actionLabel={t('parking.create')}
                onAction={() => { setEditing(null); setDialogOpen(true) }}
              />
            }
          />
        </TabsContent>

        <TabsContent value="panel" className="mt-4">
          {!lots?.length ? (
            <EmptyState
              icon={LayoutGrid}
              title={t('parking.emptyTitle')}
              description={t('parking.emptyDescription')}
              actionLabel={t('parking.create')}
              onAction={() => { setEditing(null); setDialogOpen(true) }}
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {lots.map((lot) => (
                <Card key={lot.id}>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">
                        {lot.name}
                      </CardTitle>
                      <Badge variant="outline">Lot {lot.lot_number}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {t('parking.slotRange')}: {lot.slot_start} - {lot.slot_end}
                    </p>
                  </CardHeader>
                  <CardContent>
                    <SlotGrid lot={lot} />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) setEditing(null); setDialogOpen(open) }}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('parking.edit') : t('parking.create')}</DialogTitle>
          </DialogHeader>
          <ParkingLotForm
            lot={editing}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('parking.deleteTitle')}
        description={
          bulkDeleting.length > 0
            ? t('parking.bulkDeleteConfirm', { count: bulkDeleting.length })
            : t('parking.deleteConfirm', { name: deleting?.name })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
