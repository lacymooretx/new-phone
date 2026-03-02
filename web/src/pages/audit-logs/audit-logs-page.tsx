import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useAuditLogs, type AuditLogFilters } from "@/api/audit-logs"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { auditLogColumns } from "./audit-log-columns"
import { Input } from "@/components/ui/input"
import { FileText } from "lucide-react"
import { EmptyState } from "@/components/shared/empty-state"

export function AuditLogsPage() {
  const { t } = useTranslation()
  const [filters, setFilters] = useState<AuditLogFilters>({ per_page: 50, page: 1 })

  const { data: logs, isLoading } = useAuditLogs(filters)

  const toolbar = (
    <div className="flex flex-wrap items-center gap-2">
      <Input
        className="w-40"
        placeholder="Action"
        value={filters.action ?? ""}
        onChange={(e) => setFilters((f) => ({ ...f, action: e.target.value || undefined, page: 1 }))}
      />
      <Input
        className="w-40"
        placeholder="Resource type"
        value={filters.resource_type ?? ""}
        onChange={(e) => setFilters((f) => ({ ...f, resource_type: e.target.value || undefined, page: 1 }))}
      />
      <Input
        type="date"
        className="w-40"
        value={filters.date_from ?? ""}
        onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value || undefined, page: 1 }))}
        placeholder="From"
      />
      <Input
        type="date"
        className="w-40"
        value={filters.date_to ?? ""}
        onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value || undefined, page: 1 }))}
        placeholder="To"
      />
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader title={t('auditLogs.title')} description={t('auditLogs.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('auditLogs.title') }]} />
      <DataTable
        columns={auditLogColumns}
        data={logs ?? []}
        isLoading={isLoading}
        searchPlaceholder={t('auditLogs.searchPlaceholder')}
        toolbar={toolbar}
        emptyState={<EmptyState icon={FileText} title={t('auditLogs.emptyTitle')} description={t('auditLogs.emptyDescription')} />}
        manualPagination
        pageCount={Math.ceil((logs?.length ?? 0) / (filters.per_page ?? 50)) || 1}
        onPaginationChange={(pageIndex, pageSize) =>
          setFilters((f) => ({ ...f, per_page: pageSize, page: pageIndex + 1 }))
        }
      />
    </div>
  )
}
