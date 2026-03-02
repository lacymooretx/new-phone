import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router"
import { useAIAgentStats, useAIAgentProviders, useAIAgentConversations } from "@/api/ai-agents"
import { PageHeader } from "@/components/shared/page-header"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Phone,
  Clock,
  BarChart3,
  ArrowRight,
  Bot,
  PhoneForwarded,
  Activity,
  Zap,
  CheckCircle,
  XCircle,
  CircleDashed,
} from "lucide-react"

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, "0")}`
}

function formatMs(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function outcomeVariant(outcome: string): "default" | "secondary" | "destructive" | "outline" {
  switch (outcome) {
    case "resolved":
    case "completed":
      return "default"
    case "transferred":
      return "secondary"
    case "abandoned":
    case "error":
      return "destructive"
    default:
      return "outline"
  }
}

function providerStatusIcon(status: "connected" | "error" | "unconfigured") {
  switch (status) {
    case "connected":
      return <CheckCircle className="h-4 w-4 text-green-500" />
    case "error":
      return <XCircle className="h-4 w-4 text-destructive" />
    case "unconfigured":
      return <CircleDashed className="h-4 w-4 text-muted-foreground" />
  }
}

export function AIAgentDashboardPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data: stats, isLoading: statsLoading } = useAIAgentStats()
  const { data: providers } = useAIAgentProviders()
  const { data: recentConversations, isLoading: convLoading } = useAIAgentConversations({
    limit: "5",
    offset: "0",
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("aiAgents.dashboard.title")}
        description={t("aiAgents.dashboard.description")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "AI Agents" }, { label: t("aiAgents.dashboard.title") }]}
      >
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate("/ai-agents/contexts")}>
            <Bot className="mr-2 h-4 w-4" /> {t("aiAgents.dashboard.manageAgents")}
          </Button>
          <Button variant="outline" onClick={() => navigate("/ai-agents/providers")}>
            <Activity className="mr-2 h-4 w-4" /> {t("aiAgents.dashboard.manageProviders")}
          </Button>
        </div>
      </PageHeader>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statsLoading ? (
          <>
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
          </>
        ) : (
          <>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {t("aiAgents.dashboard.callsToday")}
                </CardTitle>
                <Phone className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats?.calls_today ?? 0}</div>
                <p className="text-xs text-muted-foreground">
                  {t("aiAgents.dashboard.callsWeek", { count: stats?.calls_this_week ?? 0 })} / {t("aiAgents.dashboard.callsMonth", { count: stats?.calls_this_month ?? 0 })}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {t("aiAgents.dashboard.avgDuration")}
                </CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {stats ? formatDuration(stats.avg_duration_seconds) : "--:--"}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {t("aiAgents.dashboard.avgLatency")}
                </CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {stats ? formatMs(stats.avg_turn_response_ms) : "\u2014"}
                </div>
                <p className="text-xs text-muted-foreground">
                  {t("aiAgents.dashboard.perTurn")}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {t("aiAgents.dashboard.transferRate")}
                </CardTitle>
                <PhoneForwarded className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {stats ? `${(stats.transfer_rate * 100).toFixed(1)}%` : "\u2014"}
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* Outcome Breakdown & Provider Status */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Outcome Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4" />
                {t("aiAgents.dashboard.outcomeBreakdown")}
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-40" />
            ) : stats?.outcomes && Object.keys(stats.outcomes).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(stats.outcomes)
                  .sort(([, a], [, b]) => b - a)
                  .map(([outcome, count]) => {
                    const total = Object.values(stats.outcomes).reduce((s, v) => s + v, 0)
                    const pct = total > 0 ? ((count / total) * 100).toFixed(1) : "0"
                    return (
                      <div key={outcome} className="space-y-1">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Badge variant={outcomeVariant(outcome)}>{outcome}</Badge>
                          </div>
                          <span className="text-sm font-medium">
                            {count} ({pct}%)
                          </span>
                        </div>
                        <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary rounded-full transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                {t("aiAgents.dashboard.noOutcomeData")}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Provider Status */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4" />
                {t("aiAgents.dashboard.providerStatus")}
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {providers && providers.length > 0 ? (
              <div className="space-y-3">
                {providers.map((provider) => (
                  <div
                    key={provider.name}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <div className="flex items-center gap-2">
                      {providerStatusIcon(provider.status)}
                      <span className="font-medium text-sm">{provider.display_name}</span>
                    </div>
                    <Badge
                      variant={
                        provider.status === "connected"
                          ? "default"
                          : provider.status === "error"
                            ? "destructive"
                            : "secondary"
                      }
                    >
                      {t(`aiAgents.providers.status_${provider.status}`)}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                {t("aiAgents.dashboard.noProviders")}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Conversations */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">{t("aiAgents.dashboard.recentConversations")}</CardTitle>
          <Button
            variant="ghost"
            size="sm"
            className="text-xs"
            onClick={() => navigate("/ai-agents/conversations")}
          >
            {t("aiAgents.dashboard.viewAll")} <ArrowRight className="ml-1 h-3 w-3" />
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {convLoading ? (
            <div className="p-6 space-y-2">
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
            </div>
          ) : recentConversations && recentConversations.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("aiAgents.conversations.colDate")}</TableHead>
                  <TableHead>{t("aiAgents.conversations.colCaller")}</TableHead>
                  <TableHead>{t("aiAgents.conversations.colDuration")}</TableHead>
                  <TableHead>{t("aiAgents.conversations.colOutcome")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentConversations.map((conv) => (
                  <TableRow
                    key={conv.id}
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => navigate(`/ai-agents/conversations/${conv.id}`)}
                  >
                    <TableCell className="text-sm">
                      {new Date(conv.started_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-sm font-medium">{conv.caller_number}</TableCell>
                    <TableCell className="text-sm">{formatDuration(conv.duration_seconds)}</TableCell>
                    <TableCell>
                      <Badge variant={outcomeVariant(conv.outcome)}>{conv.outcome}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="p-6 text-sm text-muted-foreground text-center">
              {t("aiAgents.dashboard.noRecentConversations")}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
