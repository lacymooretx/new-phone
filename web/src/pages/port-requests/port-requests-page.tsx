import { useState } from "react"
import { useTranslation } from "react-i18next"
import { usePortRequests, type PortRequest } from "@/api/port-requests"
import { PageHeader } from "@/components/shared/page-header"
import { DataTable } from "@/components/data-table/data-table"
import { getPortRequestColumns } from "./port-request-columns"
import { CreatePortRequestDialog } from "./create-port-request-dialog"
import { PortRequestDetailDialog } from "./port-request-detail-dialog"
import { Button } from "@/components/ui/button"
import { Plus, ArrowRightLeft } from "lucide-react"
import { EmptyState } from "@/components/shared/empty-state"

export function PortRequestsPage() {
  const { t } = useTranslation()
  const { data: portRequests, isLoading, isError, error } = usePortRequests()

  const [createOpen, setCreateOpen] = useState(false)
  const [viewing, setViewing] = useState<PortRequest | null>(null)

  const columns = getPortRequestColumns({
    onView: (pr) => setViewing(pr),
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("portRequests.title")}
        description={t("portRequests.description")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t("portRequests.title") }]}
      >
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="mr-2 h-4 w-4" /> {t("portRequests.create")}
        </Button>
      </PageHeader>

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t("common.failedToLoad", { message: error?.message || t("common.unknownError") })}
        </div>
      )}

      <DataTable
        columns={columns}
        data={portRequests ?? []}
        isLoading={isLoading}
        searchPlaceholder={t("portRequests.searchPlaceholder")}
        emptyState={
          <EmptyState
            icon={ArrowRightLeft}
            title={t("portRequests.emptyTitle")}
            description={t("portRequests.emptyDescription")}
            actionLabel={t("portRequests.create")}
            onAction={() => setCreateOpen(true)}
          />
        }
      />

      <CreatePortRequestDialog open={createOpen} onOpenChange={setCreateOpen} />
      <PortRequestDetailDialog portRequest={viewing} onOpenChange={(open) => { if (!open) setViewing(null) }} />
    </div>
  )
}
