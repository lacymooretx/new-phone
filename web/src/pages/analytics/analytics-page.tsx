import { useState } from "react"
import { useTranslation } from "react-i18next"
import { PageHeader } from "@/components/shared/page-header"
import {
  useCallSummary,
  useCallVolumeTrend,
  useExtensionActivity,
  useDIDUsage,
  useDurationDistribution,
  useTopCallers,
  useHourlyDistribution,
} from "@/api/analytics"
import { DateRangePicker, type DateRange } from "./date-range-picker"
import { AnalyticsSummaryCards } from "./analytics-summary-cards"
import { AnalyticsCharts } from "./analytics-charts"
import { AnalyticsTables } from "./analytics-tables"

function defaultRange(): DateRange {
  const now = new Date()
  const from = new Date(now.getTime() - 7 * 86400000)
  return {
    from: from.toISOString().slice(0, 10),
    to: now.toISOString().slice(0, 10),
  }
}

export function AnalyticsPage() {
  const { t } = useTranslation()
  const [range, setRange] = useState<DateRange>(defaultRange)

  const filters = {
    date_from: `${range.from}T00:00:00Z`,
    date_to: `${range.to}T23:59:59Z`,
  }

  const { data: summary, isLoading: summaryLoading } = useCallSummary(filters)
  const { data: trend, isLoading: trendLoading } = useCallVolumeTrend({
    ...filters,
    granularity: "daily",
  })
  const { data: extensions, isLoading: extLoading } =
    useExtensionActivity(filters)
  const { data: dids, isLoading: didsLoading } = useDIDUsage(filters)
  const { data: duration, isLoading: durLoading } =
    useDurationDistribution(filters)
  const { data: callers, isLoading: callersLoading } = useTopCallers(filters)
  const { data: hourly, isLoading: hourlyLoading } =
    useHourlyDistribution(filters)

  const dispositionData = summary
    ? [
        { name: "answered", value: summary.answered },
        { name: "no_answer", value: summary.no_answer },
        { name: "busy", value: summary.busy },
        { name: "failed", value: summary.failed },
        { name: "voicemail", value: summary.voicemail },
        { name: "cancelled", value: summary.cancelled },
      ].filter((d) => d.value > 0)
    : []

  const directionData = summary
    ? [
        { name: "inbound", value: summary.inbound },
        { name: "outbound", value: summary.outbound },
        { name: "internal", value: summary.internal },
      ].filter((d) => d.value > 0)
    : []

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("analytics.title")}
        description={t("analytics.description")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Analytics" }]}
      >
        <DateRangePicker value={range} onChange={setRange} />
      </PageHeader>

      <AnalyticsSummaryCards summary={summary} isLoading={summaryLoading} />

      <AnalyticsCharts
        dispositionData={dispositionData}
        directionData={directionData}
        summaryLoading={summaryLoading}
        trend={trend}
        trendLoading={trendLoading}
        duration={duration}
        durLoading={durLoading}
        hourly={hourly}
        hourlyLoading={hourlyLoading}
      />

      <AnalyticsTables
        extensions={extensions}
        extLoading={extLoading}
        dids={dids}
        didsLoading={didsLoading}
        callers={callers}
        callersLoading={callersLoading}
      />
    </div>
  )
}
