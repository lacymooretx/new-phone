import { useTranslation } from "react-i18next"
import { useNavigate, useParams } from "react-router"
import { useAIAgentConversation } from "@/api/ai-agents"
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
import { ArrowLeft, Bot, User, Wrench, Clock, Phone, BarChart3 } from "lucide-react"

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, "0")}`
}

function formatMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`
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

export function AIAgentConversationDetailPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const { data: conversation, isLoading, isError, error } = useAIAgentConversation(id ?? "")

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (isError || !conversation) {
    return (
      <div className="space-y-6">
        <PageHeader title={t("aiAgents.conversations.detailTitle")} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "AI Agents" }, { label: t("aiAgents.conversations.detailTitle") }]}>
          <Button variant="outline" onClick={() => navigate("/ai-agents/conversations")}>
            <ArrowLeft className="mr-2 h-4 w-4" /> {t("aiAgents.conversations.backToList")}
          </Button>
        </PageHeader>
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t("common.failedToLoad", { message: error?.message || t("common.unknownError") })}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("aiAgents.conversations.detailTitle")}
        description={`${conversation.caller_number} - ${new Date(conversation.started_at).toLocaleString()}`}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "AI Agents" }, { label: t("aiAgents.conversations.detailTitle") }]}
      >
        <Button variant="outline" onClick={() => navigate("/ai-agents/conversations")}>
          <ArrowLeft className="mr-2 h-4 w-4" /> {t("aiAgents.conversations.backToList")}
        </Button>
      </PageHeader>

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t("aiAgents.conversations.colDuration")}</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatDuration(conversation.duration_seconds)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t("aiAgents.conversations.colTurns")}</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{conversation.turn_count}</div>
            <p className="text-xs text-muted-foreground">
              {t("aiAgents.conversations.bargeIns", { count: conversation.barge_in_count })}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t("aiAgents.conversations.colOutcome")}</CardTitle>
            <Phone className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <Badge variant={outcomeVariant(conversation.outcome)} className="text-lg">
              {conversation.outcome}
            </Badge>
            {conversation.transferred_to && (
              <p className="text-xs text-muted-foreground mt-1">
                {t("aiAgents.conversations.transferredTo", { target: conversation.transferred_to })}
              </p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t("aiAgents.conversations.cost")}</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {conversation.provider_cost_usd != null
                ? `$${conversation.provider_cost_usd.toFixed(4)}`
                : "\u2014"}
            </div>
            <p className="text-xs text-muted-foreground">{conversation.provider_name}</p>
          </CardContent>
        </Card>
      </div>

      {/* Summary */}
      {conversation.summary && (
        <Card>
          <CardHeader>
            <CardTitle>{t("aiAgents.conversations.summary")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm">{conversation.summary}</p>
          </CardContent>
        </Card>
      )}

      {/* Latency Metrics */}
      {conversation.latency_metrics && Object.keys(conversation.latency_metrics).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t("aiAgents.conversations.latencyMetrics")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(conversation.latency_metrics).map(([key, value]) => (
                <div key={key} className="rounded-lg border p-3 text-center">
                  <p className="text-lg font-bold">{formatMs(value)}</p>
                  <p className="text-xs text-muted-foreground">{key.replace(/_/g, " ")}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Transcript */}
      <Card>
        <CardHeader>
          <CardTitle>{t("aiAgents.conversations.transcript")}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 max-h-[600px] overflow-y-auto">
            {conversation.transcript.map((entry, idx) => {
              const isAgent = entry.speaker === "agent" || entry.speaker === "assistant"
              return (
                <div
                  key={idx}
                  className={`flex gap-3 ${isAgent ? "" : "flex-row-reverse"}`}
                >
                  <div className="flex-shrink-0 mt-1">
                    {isAgent ? (
                      <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                        <Bot className="h-4 w-4 text-primary" />
                      </div>
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                        <User className="h-4 w-4 text-muted-foreground" />
                      </div>
                    )}
                  </div>
                  <div
                    className={`rounded-lg p-3 max-w-[75%] ${
                      isAgent
                        ? "bg-primary/5 border border-primary/10"
                        : "bg-muted"
                    }`}
                  >
                    <p className="text-sm">{entry.text}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatMs(entry.timestamp_ms)}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Tool Calls */}
      {conversation.tool_calls && conversation.tool_calls.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t("aiAgents.conversations.toolCalls")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {conversation.tool_calls.map((call, idx) => (
                <div key={idx} className="rounded-lg border p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <Wrench className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium text-sm">{call.tool_name}</span>
                    <span className="text-xs text-muted-foreground">{formatMs(call.timestamp_ms)}</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">
                        {t("aiAgents.conversations.toolParams")}
                      </p>
                      <pre className="text-xs bg-muted rounded p-2 overflow-x-auto">
                        {JSON.stringify(call.params, null, 2)}
                      </pre>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">
                        {t("aiAgents.conversations.toolResult")}
                      </p>
                      <pre className="text-xs bg-muted rounded p-2 overflow-x-auto">
                        {JSON.stringify(call.result, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
