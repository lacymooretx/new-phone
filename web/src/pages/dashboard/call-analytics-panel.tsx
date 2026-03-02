import { useTranslation } from "react-i18next"
import { useCallSummary, useCallVolumeTrend } from "@/api/analytics"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from "recharts"

const DISPOSITION_COLORS: Record<string, string> = {
  answered: "hsl(142, 71%, 45%)",
  no_answer: "hsl(48, 96%, 53%)",
  busy: "hsl(25, 95%, 53%)",
  failed: "hsl(0, 72%, 51%)",
  voicemail: "hsl(262, 52%, 47%)",
  cancelled: "hsl(215, 14%, 60%)",
}

export function CallAnalyticsPanel() {
  const { t } = useTranslation()
  const { data: summary, isLoading: summaryLoading } = useCallSummary()
  const { data: trend, isLoading: trendLoading } = useCallVolumeTrend({ granularity: "daily" })

  const isLoading = summaryLoading || trendLoading

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

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (!summary || summary.total_calls === 0) return null

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t('dashboard.callVolumeByDay')}</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={trend?.data ?? []} margin={{ top: 4, right: 4, bottom: 4, left: -20 }}>
              <XAxis
                dataKey="period"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: string) => v.slice(5)}
              />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="inbound" fill="hsl(210, 79%, 56%)" name={t('dashboard.inbound')} stackId="a" />
              <Bar dataKey="outbound" fill="hsl(142, 71%, 45%)" name={t('dashboard.outbound')} stackId="a" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t('dashboard.dispositionBreakdown')}</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={dispositionData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
                label={(props: { name?: string; percent?: number }) =>
                  `${props.name ?? ""} ${((props.percent ?? 0) * 100).toFixed(0)}%`
                }
                labelLine={false}
              >
                {dispositionData.map((entry) => (
                  <Cell key={entry.name} fill={DISPOSITION_COLORS[entry.name] ?? "hsl(215, 14%, 60%)"} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
