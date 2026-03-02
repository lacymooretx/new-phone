import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useRecordings, useDeleteRecording, type RecordingFilters } from "@/api/recordings"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { recordingColumns } from "./recording-columns"
import { AudioPlayer } from "@/components/shared/audio-player"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { apiClient } from "@/lib/api-client"
import { useAuthStore } from "@/stores/auth-store"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Trash2, Disc, Download } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"
import { exportToCsv } from "@/lib/export-csv"

export function RecordingsPage() {
  const { t } = useTranslation()
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const [filters, setFilters] = useState<RecordingFilters>({})
  const { data: recordings, isLoading, isError, error } = useRecordings(filters)
  const deleteMutation = useDeleteRecording()
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const handleDelete = (id: string) => {
    setDeletingId(id)
    setConfirmOpen(true)
  }

  const confirmDelete = () => {
    if (!deletingId) return
    deleteMutation.mutate(deletingId, {
      onSuccess: () => { setConfirmOpen(false); setDeletingId(null); toast.success(t('toast.deleted', { item: t('recordings.title') })) },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleExport = () => {
    if (!recordings?.length) {
      toast.error(t('recordings.noRecordings', { defaultValue: 'No recordings to export' }))
      return
    }
    exportToCsv(
      recordings,
      [
        { key: "call_id", label: "Call ID" },
        { key: "duration_seconds", label: "Duration (s)" },
        { key: "format", label: "Format" },
        { key: "recording_policy", label: "Policy" },
        { key: "created_at", label: "Created At" },
      ],
      "recordings"
    )
    toast.success(t('toast.exportSuccess'))
  }

  const toolbar = (
    <div className="flex flex-wrap items-center gap-2">
      <Input
        type="date"
        className="w-40"
        value={filters.date_from?.slice(0, 10) ?? ""}
        onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value || undefined }))}
        placeholder="From"
      />
      <Input
        type="date"
        className="w-40"
        value={filters.date_to?.slice(0, 10) ?? ""}
        onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value || undefined }))}
        placeholder="To"
      />
      <Button variant="outline" size="sm" onClick={handleExport}>
        <Download className="mr-2 h-4 w-4" /> {t('common.exportCsv')}
      </Button>
    </div>
  )

  const allColumns = [
    ...recordingColumns,
    {
      id: "play",
      header: "",
      cell: ({ row }: any) => (
        <AudioPlayer
          fetchUrl={() => apiClient.get(`tenants/${tenantId}/recordings/${row.original.id}/playback`)}
        />
      ),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }: any) => (
        <Button
          variant="ghost"
          size="icon"
          onClick={() => handleDelete(row.original.id)}
        >
          <Trash2 className="h-4 w-4 text-destructive" />
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader title={t('recordings.title')} description={t('recordings.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('recordings.title') }]} />

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={allColumns}
        data={recordings ?? []}
        isLoading={isLoading}
        searchPlaceholder={t('recordings.searchPlaceholder')}
        toolbar={toolbar}
        emptyState={<EmptyState icon={Disc} title={t('recordings.emptyTitle')} description={t('recordings.emptyDescription')} />}
      />

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('recordings.deleteTitle')}
        description={t('recordings.deleteConfirm')}
        confirmLabel={t('common.delete')}
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  )
}
