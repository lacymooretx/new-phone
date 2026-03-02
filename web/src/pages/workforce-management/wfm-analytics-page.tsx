import { useState, useMemo, useEffect } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { TrendingUp, Save } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { PageHeader } from "@/components/shared/page-header"
import { useQueues } from "@/api/queues"
import {
  useWfmHourlyVolume,
  useWfmDailyVolume,
  useWfmForecast,
  useWfmForecastConfigs,
  useUpsertWfmForecastConfig,
  useWfmStaffingSummary,
  type WfmForecastConfigCreate,
} from "@/api/workforce-management"

const DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

function defaultDateFrom(): string {
  const d = new Date()
  d.setDate(d.getDate() - 56) // 8 weeks
  return d.toISOString().split("T")[0]
}

function defaultDateTo(): string {
  return new Date().toISOString().split("T")[0]
}

function formatHour(hour: number): string {
  const suffix = hour >= 12 ? "PM" : "AM"
  const h = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour
  return `${h}:00 ${suffix}`
}

export function WfmAnalyticsPage() {
  const { t } = useTranslation()

  // Filters
  const [selectedQueue, setSelectedQueue] = useState("")
  const [dateFrom, setDateFrom] = useState(defaultDateFrom)
  const [dateTo, setDateTo] = useState(defaultDateTo)

  // Queues
  const { data: queues } = useQueues()

  // Analytics queries (enabled only when queue selected)
  const hourlyVolume = useWfmHourlyVolume(selectedQueue, dateFrom, dateTo)
  const dailyVolume = useWfmDailyVolume(selectedQueue, dateFrom, dateTo)
  const forecast = useWfmForecast(selectedQueue)
  const forecastConfigs = useWfmForecastConfigs()
  const staffingSummary = useWfmStaffingSummary()
  const upsertConfig = useUpsertWfmForecastConfig()

  // Forecast config form state — populated from existing config when queue changes
  const existingConfig = useMemo(
    () => forecastConfigs.data?.find((c) => c.queue_id === selectedQueue),
    [forecastConfigs.data, selectedQueue]
  )

  const [configForm, setConfigForm] = useState({
    target_sla_percent: 80,
    target_sla_seconds: 20,
    shrinkage_percent: 15,
    lookback_weeks: 8,
  })

  // Sync form when existing config loads or queue changes
  useEffect(() => {
    if (existingConfig) {
      setConfigForm({
        target_sla_percent: existingConfig.target_sla_percent,
        target_sla_seconds: existingConfig.target_sla_seconds,
        shrinkage_percent: existingConfig.shrinkage_percent,
        lookback_weeks: existingConfig.lookback_weeks,
      })
    } else {
      setConfigForm({ target_sla_percent: 80, target_sla_seconds: 20, shrinkage_percent: 15, lookback_weeks: 8 })
    }
  }, [existingConfig])

  const handleSaveConfig = () => {
    if (!selectedQueue) return
    const payload: WfmForecastConfigCreate = {
      queue_id: selectedQueue,
      ...configForm,
    }
    upsertConfig.mutate(payload, {
      onSuccess: () => toast.success(t("wfm.analytics.configSaved", "Forecast config saved")),
      onError: (err) => toast.error(err.message),
    })
  }

  const isQueueSelected = !!selectedQueue

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("wfm.analytics.title", "Workforce Analytics")}
        description={t("wfm.analytics.description", "Forecast call volume and staffing requirements.")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Workforce", href: "/wfm/shifts" }, { label: t("wfm.analytics.title", "Workforce Analytics") }]}
      />

      {/* Queue + date range selectors */}
      <div className="flex flex-wrap items-end gap-4">
        <div className="space-y-1">
          <Label className="text-xs">{t("wfm.analytics.queue", "Queue")}</Label>
          <Select value={selectedQueue} onValueChange={setSelectedQueue}>
            <SelectTrigger className="w-56">
              <SelectValue placeholder={t("wfm.analytics.selectQueue", "Select a queue...")} />
            </SelectTrigger>
            <SelectContent>
              {queues?.map((q) => (
                <SelectItem key={q.id} value={q.id}>
                  {q.name} ({q.queue_number})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">{t("wfm.analytics.dateFrom", "From")}</Label>
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="w-40"
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">{t("wfm.analytics.dateTo", "To")}</Label>
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="w-40"
          />
        </div>
      </div>

      {!isQueueSelected && (
        <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
          <TrendingUp className="h-10 w-10 mb-3 opacity-40" />
          <p className="text-sm">{t("wfm.analytics.selectQueuePrompt", "Select a queue to view analytics and forecasts.")}</p>
        </div>
      )}

      {isQueueSelected && (
        <>
          {/* Hourly + Daily volume — 2 column grid on larger screens */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Hourly Volume */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  {t("wfm.analytics.hourlyVolume", "Hourly Volume")}
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {hourlyVolume.isLoading && (
                  <div className="p-6 text-sm text-muted-foreground">{t("common.loading", "Loading...")}</div>
                )}
                {hourlyVolume.isError && (
                  <div className="p-6 text-sm text-destructive">{hourlyVolume.error?.message}</div>
                )}
                {hourlyVolume.data && (
                  <div className="max-h-[480px] overflow-y-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>{t("wfm.analytics.hour", "Hour")}</TableHead>
                          <TableHead className="text-right">{t("wfm.analytics.avgCalls", "Avg Calls")}</TableHead>
                          <TableHead className="text-right">{t("wfm.analytics.avgAht", "Avg AHT (s)")}</TableHead>
                          <TableHead className="text-right">{t("wfm.analytics.avgAbandon", "Avg Abandon %")}</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {Array.from({ length: 24 }, (_, i) => {
                          const row = hourlyVolume.data.find((r) => r.hour === i)
                          return (
                            <TableRow key={i}>
                              <TableCell className="font-mono text-xs">{formatHour(i)}</TableCell>
                              <TableCell className="text-right">{row?.avg_calls.toFixed(1) ?? "0"}</TableCell>
                              <TableCell className="text-right">{row?.avg_aht_seconds.toFixed(0) ?? "0"}</TableCell>
                              <TableCell className="text-right">{row?.avg_abandon_rate != null ? `${(row.avg_abandon_rate * 100).toFixed(1)}%` : "0%"}</TableCell>
                            </TableRow>
                          )
                        })}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Daily Volume */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  {t("wfm.analytics.dailyVolume", "Daily Volume")}
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {dailyVolume.isLoading && (
                  <div className="p-6 text-sm text-muted-foreground">{t("common.loading", "Loading...")}</div>
                )}
                {dailyVolume.isError && (
                  <div className="p-6 text-sm text-destructive">{dailyVolume.error?.message}</div>
                )}
                {dailyVolume.data && (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t("wfm.analytics.day", "Day")}</TableHead>
                        <TableHead className="text-right">{t("wfm.analytics.avgCalls", "Avg Calls")}</TableHead>
                        <TableHead className="text-right">{t("wfm.analytics.avgAht", "Avg AHT (s)")}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {DAYS_OF_WEEK.map((day) => {
                        const row = dailyVolume.data.find((r) => r.day_of_week === day)
                        return (
                          <TableRow key={day}>
                            <TableCell className="font-medium">{day}</TableCell>
                            <TableCell className="text-right">{row?.avg_calls.toFixed(1) ?? "0"}</TableCell>
                            <TableCell className="text-right">{row?.avg_aht_seconds.toFixed(0) ?? "0"}</TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Forecast Config */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {t("wfm.analytics.forecastConfig", "Forecast Configuration")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="space-y-2">
                  <Label>{t("wfm.analytics.targetSlaPercent", "Target SLA %")}</Label>
                  <Input
                    type="number"
                    min={0}
                    max={100}
                    value={configForm.target_sla_percent}
                    onChange={(e) =>
                      setConfigForm((f) => ({ ...f, target_sla_percent: parseFloat(e.target.value) || 0 }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("wfm.analytics.targetSlaSeconds", "Target SLA (seconds)")}</Label>
                  <Input
                    type="number"
                    min={0}
                    value={configForm.target_sla_seconds}
                    onChange={(e) =>
                      setConfigForm((f) => ({ ...f, target_sla_seconds: parseInt(e.target.value, 10) || 0 }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("wfm.analytics.shrinkagePercent", "Shrinkage %")}</Label>
                  <Input
                    type="number"
                    min={0}
                    max={100}
                    value={configForm.shrinkage_percent}
                    onChange={(e) =>
                      setConfigForm((f) => ({ ...f, shrinkage_percent: parseFloat(e.target.value) || 0 }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("wfm.analytics.lookbackWeeks", "Lookback Weeks")}</Label>
                  <Input
                    type="number"
                    min={1}
                    max={52}
                    value={configForm.lookback_weeks}
                    onChange={(e) =>
                      setConfigForm((f) => ({ ...f, lookback_weeks: parseInt(e.target.value, 10) || 8 }))
                    }
                  />
                </div>
              </div>
              <div className="mt-4 flex justify-end">
                <Button onClick={handleSaveConfig} disabled={upsertConfig.isPending}>
                  <Save className="mr-2 h-4 w-4" />
                  {upsertConfig.isPending
                    ? t("common.saving", "Saving...")
                    : t("common.save", "Save")}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Staffing Forecast */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {t("wfm.analytics.staffingForecast", "Staffing Forecast")}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {forecast.isLoading && (
                <div className="p-6 text-sm text-muted-foreground">{t("common.loading", "Loading...")}</div>
              )}
              {forecast.isError && (
                <div className="p-6 text-sm text-destructive">{forecast.error?.message}</div>
              )}
              {forecast.data && forecast.data.length > 0 && (
                <div className="max-h-[480px] overflow-y-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t("wfm.analytics.hour", "Hour")}</TableHead>
                        <TableHead className="text-right">{t("wfm.analytics.predictedCalls", "Predicted Calls")}</TableHead>
                        <TableHead className="text-right">{t("wfm.analytics.recommendedAgents", "Recommended Agents")}</TableHead>
                        <TableHead className="text-right">{t("wfm.analytics.slaTarget", "SLA Target")}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {Array.from({ length: 24 }, (_, i) => {
                        const row = forecast.data.find((r) => r.hour === i)
                        return (
                          <TableRow key={i}>
                            <TableCell className="font-mono text-xs">{formatHour(i)}</TableCell>
                            <TableCell className="text-right">{row?.predicted_calls.toFixed(1) ?? "0"}</TableCell>
                            <TableCell className="text-right font-medium">{row?.recommended_agents ?? 0}</TableCell>
                            <TableCell className="text-right">
                              {row ? `${row.target_sla_percent}% / ${row.target_sla_seconds}s` : "-"}
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
              {forecast.data && forecast.data.length === 0 && (
                <div className="p-6 text-sm text-muted-foreground text-center">
                  {t("wfm.analytics.noForecast", "No forecast data available. Save a forecast config first.")}
                </div>
              )}
            </CardContent>
          </Card>

          {/* All Queues Staffing Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {t("wfm.analytics.allQueuesSummary", "All Queues — Staffing Summary")}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {staffingSummary.isLoading && (
                <div className="p-6 text-sm text-muted-foreground">{t("common.loading", "Loading...")}</div>
              )}
              {staffingSummary.isError && (
                <div className="p-6 text-sm text-destructive">{staffingSummary.error?.message}</div>
              )}
              {staffingSummary.data && staffingSummary.data.length > 0 && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("wfm.analytics.queueName", "Queue Name")}</TableHead>
                      <TableHead className="text-right">{t("wfm.analytics.currentAgents", "Current Agents")}</TableHead>
                      <TableHead className="text-right">{t("wfm.analytics.recommendedAgents", "Recommended Agents")}</TableHead>
                      <TableHead className="text-right">{t("wfm.analytics.forecastVolume", "Forecast Volume")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {staffingSummary.data.map((row) => (
                      <TableRow key={row.queue_id}>
                        <TableCell className="font-medium">{row.queue_name}</TableCell>
                        <TableCell className="text-right">{row.current_agents}</TableCell>
                        <TableCell className="text-right font-medium">{row.recommended_agents}</TableCell>
                        <TableCell className="text-right">{row.forecast_volume}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
              {staffingSummary.data && staffingSummary.data.length === 0 && (
                <div className="p-6 text-sm text-muted-foreground text-center">
                  {t("wfm.analytics.noSummary", "No staffing summary available.")}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
