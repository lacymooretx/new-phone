import { useTranslation } from "react-i18next"
import {
  Building2,
  Phone,
  PhoneCall,
  Users,
  CheckCircle2,
  XCircle,
} from "lucide-react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import { PageHeader } from "@/components/shared/page-header"
import { StatCard } from "@/pages/dashboard/stat-card"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { useMSPOverview } from "@/api/analytics"
import { useHealth } from "@/api/tenants"

export function MSPOverviewPage() {
  const { t } = useTranslation()
  const { data: overview, isLoading } = useMSPOverview()
  const { data: health } = useHealth()

  const topTenants = [...(overview?.tenants ?? [])]
    .sort((a, b) => b.total_calls - a.total_calls)
    .slice(0, 10)

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("mspOverview.title")}
        description={t("mspOverview.description")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "MSP Overview" }]}
      />

      {/* Platform stat cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {isLoading ? (
          <>
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
          </>
        ) : (
          <>
            <StatCard
              title={t("mspOverview.totalTenants")}
              value={overview?.total_tenants ?? 0}
              icon={Building2}
            />
            <StatCard
              title={t("mspOverview.callsToday")}
              value={overview?.total_calls_today ?? 0}
              icon={Phone}
            />
            <StatCard
              title={t("mspOverview.callsThisWeek")}
              value={overview?.total_calls_week ?? 0}
              icon={PhoneCall}
            />
            <StatCard
              title={t("mspOverview.totalExtensions")}
              value={overview?.total_extensions ?? 0}
              icon={Users}
            />
          </>
        )}
      </div>

      {/* System health */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            {t("mspOverview.systemHealth")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <HealthBadge
              label="PostgreSQL"
              status={health?.database ?? "unknown"}
            />
            <HealthBadge label="Redis" status={health?.redis ?? "unknown"} />
            <HealthBadge
              label="FreeSWITCH"
              status={health?.freeswitch ?? "unknown"}
            />
          </div>
        </CardContent>
      </Card>

      {/* Top tenants by volume chart */}
      {topTenants.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">
              {t("mspOverview.topTenantsByVolume")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={topTenants}
                margin={{ top: 4, right: 4, bottom: 4, left: -20 }}
                layout="vertical"
              >
                <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="tenant_name"
                  tick={{ fontSize: 11 }}
                  width={120}
                />
                <Tooltip />
                <Bar
                  dataKey="total_calls"
                  fill="hsl(210, 79%, 56%)"
                  name={t("mspOverview.totalCalls")}
                  radius={[0, 4, 4, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Tenant breakdown grid */}
      <div>
        <h2 className="text-lg font-semibold mb-3">
          {t("mspOverview.tenantBreakdown")}
        </h2>
        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {(overview?.tenants ?? []).map((tenant) => (
              <Card key={tenant.tenant_id}>
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-sm truncate">
                      {tenant.tenant_name}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div>
                      <div className="text-lg font-bold">
                        {tenant.total_calls}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {t("mspOverview.totalCalls")}
                      </div>
                    </div>
                    <div>
                      <div className="text-lg font-bold">
                        {tenant.calls_today}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {t("mspOverview.today")}
                      </div>
                    </div>
                    <div>
                      <div className="text-lg font-bold">
                        {tenant.extension_count}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {t("mspOverview.extensions")}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function HealthBadge({
  label,
  status,
}: {
  label: string
  status: string
}) {
  const isUp = status === "connected" || status === "healthy" || status === "ok"
  return (
    <Badge variant={isUp ? "default" : "secondary"} className="gap-1">
      {isUp ? (
        <CheckCircle2 className="h-3 w-3" />
      ) : (
        <XCircle className="h-3 w-3" />
      )}
      {label}: {status}
    </Badge>
  )
}
