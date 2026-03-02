import { useTranslation } from "react-i18next"
import { Phone, Users, Activity, PhoneCall, Clock, Plus, ArrowRight, ListOrdered, Network, BarChart3 } from "lucide-react"
import { useNavigate } from "react-router"
import { useExtensions } from "@/api/extensions"
import { useUsers } from "@/api/users"
import { useCdrs } from "@/api/cdrs"
import { useHealth } from "@/api/tenants"
import { useCallSummary } from "@/api/analytics"
import { PageHeader } from "@/components/shared/page-header"
import { StatCard } from "./stat-card"
import { QueueStatsPanel } from "./queue-stats-panel"
import { AgentStatusPanel } from "./agent-status-panel"
import { CallAnalyticsPanel } from "./call-analytics-panel"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${s.toString().padStart(2, "0")}`
}

export function DashboardPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data: extensions, isLoading: extLoading, isError: extError, error: extErrorObj } = useExtensions()
  const { data: users, isLoading: usersLoading, isError: usersError, error: usersErrorObj } = useUsers()
  const { data: cdrs, isLoading: cdrsLoading, isError: cdrsError, error: cdrsErrorObj } = useCdrs({ limit: 5 })
  const { data: health } = useHealth()
  const { data: summary, isLoading: summaryLoading } = useCallSummary()

  const dashboardError = extError || usersError || cdrsError
  const dashboardErrorMessage = extErrorObj?.message || usersErrorObj?.message || cdrsErrorObj?.message || t('common.unknownError')

  return (
    <div className="space-y-6">
      <PageHeader title={t('dashboard.title')} description={t('dashboard.description')} />

      {dashboardError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('dashboard.failedToLoadData')}: {dashboardErrorMessage}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {extLoading ? (
          <Skeleton className="h-32" />
        ) : (
          <StatCard title={t('dashboard.extensions')} value={extensions?.length ?? 0} icon={Phone} />
        )}
        {usersLoading ? (
          <Skeleton className="h-32" />
        ) : (
          <StatCard title={t('dashboard.users')} value={users?.length ?? 0} icon={Users} />
        )}
        <StatCard
          title={t('dashboard.systemHealth')}
          value={health?.status === "healthy" ? t('dashboard.healthy') : health?.status ?? "..."}
          icon={Activity}
          description={health?.services ? `DB: ${health.services.postgres?.status ?? "unknown"} | Redis: ${health.services.redis?.status ?? "unknown"}` : undefined}
        />
        {summaryLoading ? (
          <Skeleton className="h-32" />
        ) : (
          <StatCard title={t('dashboard.callsToday')} value={summary?.total_calls ?? 0} icon={PhoneCall} />
        )}
        {summaryLoading ? (
          <Skeleton className="h-32" />
        ) : (
          <StatCard
            title={t('dashboard.avgDuration')}
            value={formatDuration(summary?.avg_duration_seconds ?? 0)}
            icon={Clock}
            description={`${(summary?.no_answer ?? 0) + (summary?.cancelled ?? 0)} ${t('dashboard.missed')}`}
          />
        )}
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">{t('dashboard.quickActions')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate("/extensions")}>
              <Plus className="mr-1 h-4 w-4" /> {t('dashboard.extension')}
            </Button>
            <Button variant="outline" size="sm" onClick={() => navigate("/users")}>
              <Plus className="mr-1 h-4 w-4" /> {t('dashboard.user')}
            </Button>
            <Button variant="outline" size="sm" onClick={() => navigate("/ring-groups")}>
              <Plus className="mr-1 h-4 w-4" /> {t('dashboard.ringGroup')}
            </Button>
            <Button variant="outline" size="sm" onClick={() => navigate("/queues")}>
              <ListOrdered className="mr-1 h-4 w-4" /> {t('dashboard.queues')}
            </Button>
            <Button variant="outline" size="sm" onClick={() => navigate("/sip-trunks")}>
              <Network className="mr-1 h-4 w-4" /> {t('dashboard.sipTrunks')}
            </Button>
            <Button variant="outline" size="sm" onClick={() => navigate("/cdrs")}>
              <PhoneCall className="mr-1 h-4 w-4" /> {t('dashboard.callHistory')}
            </Button>
            <Button variant="outline" size="sm" onClick={() => navigate("/analytics")}>
              <BarChart3 className="mr-1 h-4 w-4" /> {t('dashboard.callAnalytics')}
            </Button>
          </div>
        </CardContent>
      </Card>

      <CallAnalyticsPanel />

      <QueueStatsPanel />

      <AgentStatusPanel />

      {/* Recent CDRs table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">{t('dashboard.recentCalls')}</CardTitle>
          <Button variant="ghost" size="sm" className="text-xs" onClick={() => navigate("/cdrs")}>
            {t('dashboard.viewAll')} <ArrowRight className="ml-1 h-3 w-3" />
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {cdrsLoading ? (
            <div className="p-6 space-y-2">
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
            </div>
          ) : cdrs && cdrs.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('dashboard.col.time')}</TableHead>
                  <TableHead>{t('dashboard.col.direction')}</TableHead>
                  <TableHead>{t('dashboard.col.from')}</TableHead>
                  <TableHead>{t('dashboard.col.to')}</TableHead>
                  <TableHead>{t('dashboard.col.status')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {cdrs.map((cdr) => (
                  <TableRow key={cdr.id}>
                    <TableCell className="text-sm">{new Date(cdr.start_time).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{cdr.direction}</Badge>
                    </TableCell>
                    <TableCell className="text-sm">{cdr.caller_number}</TableCell>
                    <TableCell className="text-sm">{cdr.called_number}</TableCell>
                    <TableCell>
                      <Badge variant={cdr.disposition === "answered" ? "default" : "secondary"}>
                        {cdr.disposition}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="p-6 text-sm text-muted-foreground text-center">{t('dashboard.noRecentCalls')}</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
