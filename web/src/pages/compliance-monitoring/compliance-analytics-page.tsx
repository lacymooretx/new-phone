import { useTranslation } from "react-i18next"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { PageHeader } from "@/components/shared/page-header"
import {
  useComplianceSummary,
  useComplianceAgentScores,
  useComplianceQueueScores,
  useComplianceRuleEffectiveness,
  useComplianceTrend,
} from "@/api/compliance-monitoring"

function scoreVariant(score: number | null) {
  if (score == null) return "outline"
  if (score >= 80) return "default"
  if (score >= 60) return "secondary"
  return "destructive"
}

export function ComplianceAnalyticsPage() {
  const { t } = useTranslation()
  const { data: summary } = useComplianceSummary()
  const { data: agentScores } = useComplianceAgentScores()
  const { data: queueScores } = useComplianceQueueScores()
  const { data: ruleEffectiveness } = useComplianceRuleEffectiveness()
  const { data: trend } = useComplianceTrend()

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("complianceMonitoring.analytics.title")}
        description={t("complianceMonitoring.analytics.description")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Compliance" }, { label: t("complianceMonitoring.analytics.title") }]}
      />

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {t("complianceMonitoring.analytics.totalEvaluations")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{summary.total_evaluations}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {t("complianceMonitoring.analytics.averageScore")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">
                {summary.average_score != null
                  ? `${summary.average_score.toFixed(1)}%`
                  : "-"}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {t("complianceMonitoring.analytics.flaggedRate")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{summary.flagged_rate.toFixed(1)}%</p>
              <p className="text-xs text-muted-foreground">
                {summary.flagged_count} {t("complianceMonitoring.evaluations.col.flagged").toLowerCase()}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {t("complianceMonitoring.analytics.passRate")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{summary.pass_rate.toFixed(1)}%</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Agent Scores */}
      {agentScores && agentScores.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t("complianceMonitoring.analytics.agentScores")}</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("complianceMonitoring.analytics.col.agent")}</TableHead>
                  <TableHead>{t("complianceMonitoring.analytics.col.evaluations")}</TableHead>
                  <TableHead>{t("complianceMonitoring.analytics.col.avgScore")}</TableHead>
                  <TableHead>{t("complianceMonitoring.analytics.col.flagged")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agentScores.map((agent) => (
                  <TableRow key={agent.extension_id}>
                    <TableCell className="font-medium">{agent.extension_number}</TableCell>
                    <TableCell>{agent.evaluation_count}</TableCell>
                    <TableCell>
                      <Badge variant={scoreVariant(agent.average_score)}>
                        {agent.average_score != null ? `${agent.average_score.toFixed(0)}%` : "-"}
                      </Badge>
                    </TableCell>
                    <TableCell>{agent.flagged_count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Queue Scores */}
      {queueScores && queueScores.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t("complianceMonitoring.analytics.queueScores")}</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("complianceMonitoring.analytics.col.queue")}</TableHead>
                  <TableHead>{t("complianceMonitoring.analytics.col.evaluations")}</TableHead>
                  <TableHead>{t("complianceMonitoring.analytics.col.avgScore")}</TableHead>
                  <TableHead>{t("complianceMonitoring.analytics.col.flagged")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {queueScores.map((queue) => (
                  <TableRow key={queue.queue_id}>
                    <TableCell className="font-medium">{queue.queue_name}</TableCell>
                    <TableCell>{queue.evaluation_count}</TableCell>
                    <TableCell>
                      <Badge variant={scoreVariant(queue.average_score)}>
                        {queue.average_score != null ? `${queue.average_score.toFixed(0)}%` : "-"}
                      </Badge>
                    </TableCell>
                    <TableCell>{queue.flagged_count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Rule Effectiveness */}
      {ruleEffectiveness && ruleEffectiveness.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t("complianceMonitoring.analytics.ruleEffectiveness")}</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("complianceMonitoring.analytics.col.rule")}</TableHead>
                  <TableHead>{t("complianceMonitoring.analytics.col.severity")}</TableHead>
                  <TableHead>{t("complianceMonitoring.analytics.col.total")}</TableHead>
                  <TableHead>{t("complianceMonitoring.analytics.col.passed")}</TableHead>
                  <TableHead>{t("complianceMonitoring.analytics.col.failed")}</TableHead>
                  <TableHead>{t("complianceMonitoring.analytics.col.na")}</TableHead>
                  <TableHead>{t("complianceMonitoring.analytics.col.failRate")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {ruleEffectiveness.map((rule) => (
                  <TableRow key={rule.rule_id}>
                    <TableCell className="font-medium">{rule.rule_name}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          rule.severity === "critical"
                            ? "destructive"
                            : rule.severity === "major"
                              ? "default"
                              : "secondary"
                        }
                      >
                        {rule.severity}
                      </Badge>
                    </TableCell>
                    <TableCell>{rule.total_evaluated}</TableCell>
                    <TableCell>{rule.pass_count}</TableCell>
                    <TableCell>{rule.fail_count}</TableCell>
                    <TableCell>{rule.not_applicable_count}</TableCell>
                    <TableCell>
                      <Badge variant={rule.fail_rate > 20 ? "destructive" : "outline"}>
                        {rule.fail_rate.toFixed(1)}%
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Trend */}
      {trend && trend.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t("complianceMonitoring.analytics.trend")}</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("complianceMonitoring.analytics.col.period")}</TableHead>
                  <TableHead>{t("complianceMonitoring.analytics.col.evaluations")}</TableHead>
                  <TableHead>{t("complianceMonitoring.analytics.col.avgScore")}</TableHead>
                  <TableHead>{t("complianceMonitoring.analytics.col.flagged")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {trend.map((point) => (
                  <TableRow key={point.period}>
                    <TableCell className="font-medium">{point.period}</TableCell>
                    <TableCell>{point.evaluation_count}</TableCell>
                    <TableCell>
                      <Badge variant={scoreVariant(point.average_score)}>
                        {point.average_score != null ? `${point.average_score.toFixed(0)}%` : "-"}
                      </Badge>
                    </TableCell>
                    <TableCell>{point.flagged_count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
