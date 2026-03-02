import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useTenants, useCreateTenant, useUpdateTenant, useDeactivateTenant, type Tenant, type TenantCreate, type TenantUpdate } from "@/api/tenants"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { useAuthStore } from "@/stores/auth-store"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { StatusBadge } from "@/components/shared/status-badge"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { TenantForm } from "./tenant-form"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Plus, MoreHorizontal, Pencil, Power, Building2 } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"
import type { ColumnDef } from "@tanstack/react-table"

export function TenantsPage() {
  const { t } = useTranslation()
  const { data: tenants, isLoading, isError, error } = useTenants()
  const { setActiveTenant } = useAuthStore()
  const createMutation = useCreateTenant()
  const updateMutation = useUpdateTenant()
  const deactivateMutation = useDeactivateTenant()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Tenant | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deactivating, setDeactivating] = useState<Tenant | null>(null)

  useBeforeUnload(dialogOpen)

  const handleCreate = (data: TenantCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('tenants.title_one') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: TenantCreate) => {
    if (!editing) return
    const update: { id: string } & TenantUpdate = { id: editing.id, ...data }
    updateMutation.mutate(update, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('tenants.title_one') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleExport = (data: Tenant[]) => {
    exportToCsv(data, [
      { key: "name", label: t('tenants.col.name') },
      { key: "domain", label: t('tenants.col.domain') },
      { key: "is_active", label: t('tenants.col.status') },
    ], "tenants")
  }

  const handleDeactivate = () => {
    if (!deactivating) return
    deactivateMutation.mutate(deactivating.id, {
      onSuccess: () => { setConfirmOpen(false); setDeactivating(null); toast.success(t('tenants.deactivated')) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns: ColumnDef<Tenant, unknown>[] = [
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={t('tenants.col.name')} />,
    },
    {
      accessorKey: "slug",
      header: t('tenants.col.slug'),
      cell: ({ row }) => <span className="font-mono text-sm">{row.original.slug}</span>,
    },
    {
      accessorKey: "domain",
      header: t('tenants.col.domain'),
      cell: ({ row }) => row.original.domain || "\u2014",
    },
    {
      accessorKey: "sip_domain",
      header: t('tenants.col.sipDomain'),
      cell: ({ row }) => row.original.sip_domain || "\u2014",
    },
    {
      accessorKey: "is_active",
      header: t('tenants.col.status'),
      cell: ({ row }) => <StatusBadge active={row.original.is_active} />,
    },
    {
      accessorKey: "created_at",
      header: ({ column }) => <DataTableColumnHeader column={column} title={t('tenants.col.created')} />,
      cell: ({ row }) => new Date(row.original.created_at).toLocaleDateString(),
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0" aria-label={t('common.actions')}>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => { setEditing(row.original); setDialogOpen(true) }}>
              <Pencil className="mr-2 h-4 w-4" /> {t('common.edit')}
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => { setDeactivating(row.original); setConfirmOpen(true) }}
              className="text-destructive"
            >
              <Power className="mr-2 h-4 w-4" /> {t('tenants.deactivate')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader title={t('tenants.title')} description={t('tenants.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('tenants.title') }]}>
        <Button onClick={() => { setEditing(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('tenants.createTenant')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('dashboard.failedToLoadData')}: {error?.message || t('common.unknownError')}
        </div>
      )}

      <DataTable
        columns={columns}
        data={tenants ?? []}
        isLoading={isLoading}
        searchPlaceholder={t('tenants.searchPlaceholder')}
        onRowClick={(tenant) => setActiveTenant(tenant.id)}
        onExport={handleExport}
        emptyState={<EmptyState icon={Building2} title={t('tenants.emptyTitle')} description={t('tenants.emptyDescription')} actionLabel={t('tenants.createTenant')} onAction={() => { setEditing(null); setDialogOpen(true) }} />}
      />

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('tenants.editTenant') : t('tenants.createTenant')}</DialogTitle>
          </DialogHeader>
          <TenantForm
            tenant={editing}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('tenants.deactivateTenant')}
        description={t('tenants.deactivateConfirm', { name: deactivating?.name })}
        confirmLabel={t('tenants.deactivate')}
        variant="destructive"
        onConfirm={handleDeactivate}
      />
    </div>
  )
}
