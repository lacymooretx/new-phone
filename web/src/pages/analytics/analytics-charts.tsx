import { useTranslation } from "react-i18next"
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  type CallVolumeTrendResponse,
  type DurationBucket,
  type HourlyDistributionPoint,
} from "@/api/analytics"

const DISPOSITION_COLORS: Record<string, string> = {
  answered: "hsl(142, 71%, 45%)",
  no_answer: "hsl(48, 96%, 53%)",
  busy: "hsl(25, 95%, 53%)",
  failed: "hsl(0, 72%, 51%)",
  voicemail: "hsl(262, 52%, 47%)",
  cancelled: "hsl(215, 14%, 60%)",
}

const DIRECTION_COLORS: Record<string, string> = {
  inbound: "hsl(210, 79%, 56%)",
  outbound: "hsl(142, 71%, 45%)",
  internal: "hsl(262, 52%, 47%)",
}

interface DispositionDataItem {
  name: string
  value: number
}

interface DirectionDataItem {
  name: string
  value: number
}

interface AnalyticsChartsProps {
  dispositionData: DispositionDataItem[]
  directionData: DirectionDataItem[]
  summaryLoading: boolean
  trend: CallVolumeTrendResponse | undefined
  trendLoading: boolean
  duration: DurationBucket[] | undefined
  durLoading: boolean
  hourly: HourlyDistributionPoint[] | undefined
  hourlyLoading: boolean
}

export function AnalyticsCharts({
  dispositionData,
  directionData,
  summaryLoading,
  trend,
  trendLoading,
  duration,
  durLoading,
  hourly,
  hourlyLoading,
}: AnalyticsChartsProps) {
  const { t } = useTranslation()

  return (
    <>
      {/* Call volume trend + disposition breakdown */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">
              {t("analytics.callVolumeTrend")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {trendLoading ? (
              <Skeleton className="h-[260px]" />
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart
                  data={trend?.data ?? []}
                  margin={{ top: 4, right: 4, bottom: 4, left: -20 }}
                >
                  <XAxis
                    dataKey="period"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: string) => v.slice(5, 10)}
                  />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="inbound"
                    stroke={DIRECTION_COLORS.inbound}
                    name={t("analytics.inbound")}
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="outbound"
                    stroke={DIRECTION_COLORS.outbound}
                    name={t("analytics.outbound")}
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="internal"
                    stroke={DIRECTION_COLORS.internal}
                    name={t("analytics.internal")}
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">
              {t("analytics.dispositionBreakdown")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-[260px]" />
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={dispositionData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={90}
                    paddingAngle={2}
                    dataKey="value"
                    label={(props: { name?: string; percent?: number }) =>
                      `${props.name ?? ""} ${((props.percent ?? 0) * 100).toFixed(0)}%`
                    }
                    labelLine={false}
                  >
                    {dispositionData.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={
                          DISPOSITION_COLORS[entry.name] ?? "hsl(215, 14%, 60%)"
                        }
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Direction split + Duration distribution */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">
              {t("analytics.directionSplit")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-[260px]" />
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={directionData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={90}
                    paddingAngle={2}
                    dataKey="value"
                    label={(props: { name?: string; percent?: number }) =>
                      `${props.name ?? ""} ${((props.percent ?? 0) * 100).toFixed(0)}%`
                    }
                    labelLine={false}
                  >
                    {directionData.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={
                          DIRECTION_COLORS[entry.name] ?? "hsl(215, 14%, 60%)"
                        }
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">
              {t("analytics.durationDistribution")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {durLoading ? (
              <Skeleton className="h-[260px]" />
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart
                  data={duration ?? []}
                  margin={{ top: 4, right: 4, bottom: 4, left: -20 }}
                >
                  <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Bar
                    dataKey="count"
                    fill="hsl(210, 79%, 56%)"
                    name={t("analytics.calls")}
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Hourly distribution */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            {t("analytics.hourlyDistribution")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {hourlyLoading ? (
            <Skeleton className="h-[260px]" />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={hourly ?? []}
                margin={{ top: 4, right: 4, bottom: 4, left: -20 }}
              >
                <XAxis
                  dataKey="hour"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: number) =>
                    `${v.toString().padStart(2, "0")}:00`
                  }
                />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip
                  labelFormatter={(v) =>
                    `${String(v).padStart(2, "0")}:00`
                  }
                />
                <Legend />
                <Bar
                  dataKey="inbound"
                  fill={DIRECTION_COLORS.inbound}
                  name={t("analytics.inbound")}
                  stackId="a"
                />
                <Bar
                  dataKey="outbound"
                  fill={DIRECTION_COLORS.outbound}
                  name={t("analytics.outbound")}
                  stackId="a"
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </>
  )
}
