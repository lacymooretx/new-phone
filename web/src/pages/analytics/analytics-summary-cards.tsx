import { useTranslation } from "react-i18next"
import {
  Phone,
  PhoneIncoming,
  PhoneOutgoing,
  PhoneMissed,
  Clock,
} from "lucide-react"
import { StatCard } from "@/pages/dashboard/stat-card"
import { Skeleton } from "@/components/ui/skeleton"
import { type CallSummary } from "@/api/analytics"

interface AnalyticsSummaryCardsProps {
  summary: CallSummary | undefined
  isLoading: boolean
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${s.toString().padStart(2, "0")}`
}

export function AnalyticsSummaryCards({ summary, isLoading }: AnalyticsSummaryCardsProps) {
  const { t } = useTranslation()

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
      {isLoading ? (
        <>
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </>
      ) : (
        <>
          <StatCard
            title={t("analytics.totalCalls")}
            value={summary?.total_calls ?? 0}
            icon={Phone}
          />
          <StatCard
            title={t("analytics.inboundCalls")}
            value={summary?.inbound ?? 0}
            icon={PhoneIncoming}
          />
          <StatCard
            title={t("analytics.outboundCalls")}
            value={summary?.outbound ?? 0}
            icon={PhoneOutgoing}
          />
          <StatCard
            title={t("analytics.missedCalls")}
            value={
              (summary?.no_answer ?? 0) + (summary?.cancelled ?? 0)
            }
            icon={PhoneMissed}
          />
          <StatCard
            title={t("analytics.avgDuration")}
            value={formatDuration(summary?.avg_duration_seconds ?? 0)}
            icon={Clock}
          />
        </>
      )}
    </div>
  )
}
