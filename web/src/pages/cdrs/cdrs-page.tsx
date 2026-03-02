import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useCdrs, exportCdrsAsCsv, type CDRFilters } from "@/api/cdrs"
import { useAuthStore } from "@/stores/auth-store"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { cdrColumns } from "./cdr-columns"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Download, PhoneCall } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/shared/empty-state"

export function CdrsPage() {
  const { t } = useTranslation()
  const tenantId = useAuthStore((s) => s.activeTenantId)!
  const [filters, setFilters] = useState<CDRFilters>({ limit: 50, offset: 0 })

  const { data: cdrs, isLoading, isError, error } = useCdrs(filters)

  const handleExport = async () => {
    try {
      await exportCdrsAsCsv(tenantId, filters)
      toast.success(t('toast.exportSuccess'))
    } catch {
      toast.error(t('cdrs.exportFailed', { defaultValue: 'Export failed' }))
    }
  }

  const toolbar = (
    <div className="flex flex-wrap items-center gap-2">
      <Input
        type="date"
        className="w-40"
        value={filters.date_from?.slice(0, 10) ?? ""}
        onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value || undefined, offset: 0 }))}
        placeholder="From"
      />
      <Input
        type="date"
        className="w-40"
        value={filters.date_to?.slice(0, 10) ?? ""}
        onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value || undefined, offset: 0 }))}
        placeholder="To"
      />
      <Select
        value={filters.direction ?? "all"}
        onValueChange={(v) => setFilters((f) => ({ ...f, direction: v === "all" ? undefined : v, offset: 0 }))}
      >
        <SelectTrigger className="w-32">
          <SelectValue placeholder={t('cdrs.filters.direction')} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">{t('cdrs.filters.all')}</SelectItem>
          <SelectItem value="inbound">{t('cdrs.filters.inbound')}</SelectItem>
          <SelectItem value="outbound">{t('cdrs.filters.outbound')}</SelectItem>
          <SelectItem value="internal">{t('cdrs.filters.internal')}</SelectItem>
        </SelectContent>
      </Select>
      <Select
        value={filters.disposition ?? "all"}
        onValueChange={(v) => setFilters((f) => ({ ...f, disposition: v === "all" ? undefined : v, offset: 0 }))}
      >
        <SelectTrigger className="w-36">
          <SelectValue placeholder={t('cdrs.filters.disposition', { defaultValue: 'Disposition' })} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">{t('cdrs.filters.all')}</SelectItem>
          <SelectItem value="answered">{t('cdrs.filters.answered', { defaultValue: 'Answered' })}</SelectItem>
          <SelectItem value="no_answer">{t('cdrs.filters.noAnswer', { defaultValue: 'No Answer' })}</SelectItem>
          <SelectItem value="busy">{t('cdrs.filters.busy', { defaultValue: 'Busy' })}</SelectItem>
          <SelectItem value="failed">{t('cdrs.filters.failed', { defaultValue: 'Failed' })}</SelectItem>
          <SelectItem value="voicemail">{t('cdrs.filters.voicemail', { defaultValue: 'Voicemail' })}</SelectItem>
          <SelectItem value="cancelled">{t('cdrs.filters.cancelled', { defaultValue: 'Cancelled' })}</SelectItem>
        </SelectContent>
      </Select>
      <Button variant="outline" size="sm" onClick={handleExport}>
        <Download className="mr-2 h-4 w-4" /> {t('common.exportCsv')}
      </Button>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader title={t('cdrs.title')} description={t('cdrs.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('cdrs.title') }]} />

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <DataTable
        columns={cdrColumns}
        searchPlaceholder={t('cdrs.searchPlaceholder')}
        data={cdrs ?? []}
        isLoading={isLoading}
        toolbar={toolbar}
        emptyState={<EmptyState icon={PhoneCall} title={t('cdrs.emptyTitle')} description={t('cdrs.emptyDescription')} />}
        manualPagination
        pageCount={Math.ceil((cdrs?.length ?? 0) / (filters.limit ?? 50)) || 1}
        onPaginationChange={(pageIndex, pageSize) =>
          setFilters((f) => ({ ...f, limit: pageSize, offset: pageIndex * pageSize }))
        }
      />
    </div>
  )
}
