import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useDevices, useCreateDevice, useUpdateDevice, useDeleteDevice, type Device, type DeviceCreate } from "@/api/devices"
import { useBeforeUnload } from "@/hooks/use-before-unload"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getDeviceColumns } from "./device-columns"
import { DeviceForm } from "./device-form"
import { DeviceKeysEditor } from "./device-keys-editor"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, Monitor } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

function getProvisioningUrl(device: Device): string {
  const baseUrl = window.location.origin
  const ext = device.phone_model_manufacturer?.toLowerCase() === "sangoma" ? "xml" : "cfg"
  return `${baseUrl}/provisioning/${device.mac_address}.${ext}`
}

export function DevicesPage() {
  const { t } = useTranslation()
  const { data: devices, isLoading, isError, error } = useDevices()
  const createMutation = useCreateDevice()
  const updateMutation = useUpdateDevice()
  const deleteMutation = useDeleteDevice()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Device | null>(null)
  const [keysDialogOpen, setKeysDialogOpen] = useState(false)
  const [keysDevice, setKeysDevice] = useState<Device | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState<Device | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState<Device[]>([])

  useBeforeUnload(dialogOpen || keysDialogOpen)

  const handleCreate = (data: DeviceCreate) => {
    createMutation.mutate(data, {
      onSuccess: () => { setDialogOpen(false); toast.success(t('toast.created', { item: t('devices.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleUpdate = (data: DeviceCreate) => {
    if (!editing) return
    updateMutation.mutate({ id: editing.id, ...data }, {
      onSuccess: () => { setDialogOpen(false); setEditing(null); toast.success(t('toast.updated', { item: t('devices.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleDelete = (device: Device) => {
    setDeleting(device)
    setConfirmOpen(true)
  }

  const handleBulkDelete = (rows: Device[]) => {
    setBulkDeleting(rows)
    setConfirmOpen(true)
  }

  const handleExport = (data: Device[]) => {
    exportToCsv(data, [
      { key: "mac_address", label: "MAC Address" },
      { key: "phone_model_name", label: "Model" },
      { key: "extension_number", label: "Extension" },
      { key: "name", label: "Name" },
      { key: "location", label: "Location" },
      { key: "is_active", label: "Active" },
    ], "devices")
  }

  const handleCopyProvUrl = (device: Device) => {
    const url = getProvisioningUrl(device)
    navigator.clipboard.writeText(url)
    toast.success("Provisioning URL copied to clipboard")
  }

  const confirmDelete = () => {
    if (bulkDeleting.length > 0) {
      Promise.all(bulkDeleting.map((item) => deleteMutation.mutateAsync(item.id)))
        .then(() => {
          setConfirmOpen(false)
          setBulkDeleting([])
          toast.success(t('toast.bulkDeleted', { count: bulkDeleting.length, item: t('devices.title').toLowerCase() }))
        })
        .catch((err) => toast.error(err.message))
      return
    }
    if (!deleting) return
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => { setConfirmOpen(false); setDeleting(null); toast.success(t('toast.deleted', { item: t('devices.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const columns = getDeviceColumns({
    onEdit: (d) => { setEditing(d); setDialogOpen(true) },
    onDelete: handleDelete,
    onEditKeys: (d) => { setKeysDevice(d); setKeysDialogOpen(true) },
    onCopyProvUrl: handleCopyProvUrl,
  })

  return (
    <div className="space-y-6">
      <PageHeader title={t('devices.title')} description={t('devices.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('devices.title') }]}>
        <Button onClick={() => { setEditing(null); setDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" /> {t('devices.create')}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={columns}
        data={devices ?? []}
        isLoading={isLoading}
        searchPlaceholder={t('devices.searchPlaceholder')}
        enableRowSelection
        onBulkDelete={handleBulkDelete}
        onExport={handleExport}
        emptyState={<EmptyState icon={Monitor} title={t('devices.emptyTitle')} description={t('devices.emptyDescription')} actionLabel={t('devices.create')} onAction={() => { setEditing(null); setDialogOpen(true) }} />}
      />

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) setEditing(null); setDialogOpen(open) }}>
        <DialogContent className="max-w-2xl" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{editing ? t('devices.edit') : t('devices.create')}</DialogTitle>
          </DialogHeader>
          <DeviceForm
            device={editing}
            onSubmit={editing ? handleUpdate : handleCreate}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      {/* Line Keys Editor Dialog */}
      <Dialog open={keysDialogOpen} onOpenChange={(open) => { if (!open) setKeysDevice(null); setKeysDialogOpen(open) }}>
        <DialogContent className="max-w-3xl" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>
              {t('devices.form.lineKeys')} — {keysDevice?.name || keysDevice?.mac_address}
            </DialogTitle>
          </DialogHeader>
          {keysDevice && (
            <DeviceKeysEditor device={keysDevice} onClose={() => setKeysDialogOpen(false)} />
          )}
        </DialogContent>
      </Dialog>

      {/* Confirm Delete */}
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('devices.deleteTitle')}
        description={
          bulkDeleting.length > 0
            ? t('devices.bulkDeleteConfirm', { count: bulkDeleting.length })
            : t('devices.deleteConfirm', { name: deleting?.name || deleting?.mac_address })
        }
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
