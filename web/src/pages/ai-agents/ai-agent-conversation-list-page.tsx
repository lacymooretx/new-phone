import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router"
import { useAIAgentConversations, type AIAgentConversation } from "@/api/ai-agents"
import { PageHeader } from "@/components/shared/page-header"
import { EmptyState } from "@/components/shared/empty-state"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { MessageSquare, ChevronLeft, ChevronRight } from "lucide-react"

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, "0")}`
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

export function AIAgentConversationListPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [outcomeFilter, setOutcomeFilter] = useState<string>("")
  const [callerFilter, setCallerFilter] = useState("")
  const [page, setPage] = useState(0)
  const pageSize = 25

  const params: Record<string, string> = {}
  if (outcomeFilter) params.outcome = outcomeFilter
  if (callerFilter) params.caller_number = callerFilter
  params.offset = (page * pageSize).toString()
  params.limit = pageSize.toString()

  const { data: conversations, isLoading, isError, error } = useAIAgentConversations(
    Object.keys(params).length > 0 ? params : undefined
  )

  const handleRowClick = (conv: AIAgentConversation) => {
    navigate(`/ai-agents/conversations/${conv.id}`)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("aiAgents.conversations.title")}
        description={t("aiAgents.conversations.description")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "AI Agents" }, { label: t("aiAgents.conversations.title") }]}
      />

      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t("common.failedToLoad", { message: error?.message || t("common.unknownError") })}
        </div>
      )}

      <div className="flex items-center gap-4">
        <Input
          placeholder={t("aiAgents.conversations.searchCaller")}
          value={callerFilter}
          onChange={(e) => { setCallerFilter(e.target.value); setPage(0) }}
          className="max-w-sm"
        />
        <Select value={outcomeFilter} onValueChange={(v) => { setOutcomeFilter(v === "all" ? "" : v); setPage(0) }}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder={t("aiAgents.conversations.filterOutcome")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("aiAgents.conversations.allOutcomes")}</SelectItem>
            <SelectItem value="resolved">{t("aiAgents.conversations.outcomeResolved")}</SelectItem>
            <SelectItem value="transferred">{t("aiAgents.conversations.outcomeTransferred")}</SelectItem>
            <SelectItem value="abandoned">{t("aiAgents.conversations.outcomeAbandoned")}</SelectItem>
            <SelectItem value="error">{t("aiAgents.conversations.outcomeError")}</SelectItem>
            <SelectItem value="completed">{t("aiAgents.conversations.outcomeCompleted")}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : !conversations || conversations.length === 0 ? (
        <EmptyState
          icon={MessageSquare}
          title={t("aiAgents.conversations.emptyTitle")}
          description={t("aiAgents.conversations.emptyDescription")}
        />
      ) : (
        <>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("aiAgents.conversations.colDate")}</TableHead>
                  <TableHead>{t("aiAgents.conversations.colCaller")}</TableHead>
                  <TableHead>{t("aiAgents.conversations.colProvider")}</TableHead>
                  <TableHead>{t("aiAgents.conversations.colDuration")}</TableHead>
                  <TableHead>{t("aiAgents.conversations.colTurns")}</TableHead>
                  <TableHead>{t("aiAgents.conversations.colOutcome")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {conversations.map((conv) => (
                  <TableRow
                    key={conv.id}
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => handleRowClick(conv)}
                  >
                    <TableCell className="text-sm">
                      {new Date(conv.started_at).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <div>
                        <span className="font-medium">{conv.caller_number}</span>
                        {conv.caller_name && (
                          <span className="text-muted-foreground text-sm ml-2">{conv.caller_name}</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{conv.provider_name}</Badge>
                    </TableCell>
                    <TableCell className="text-sm">{formatDuration(conv.duration_seconds)}</TableCell>
                    <TableCell className="text-sm">{conv.turn_count}</TableCell>
                    <TableCell>
                      <Badge variant={outcomeVariant(conv.outcome)}>{conv.outcome}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {t("aiAgents.conversations.showingPage", { page: page + 1 })}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage(page - 1)}
              >
                <ChevronLeft className="h-4 w-4 mr-1" /> {t("aiAgents.conversations.prev")}
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={conversations.length < pageSize}
                onClick={() => setPage(page + 1)}
              >
                {t("aiAgents.conversations.next")} <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
