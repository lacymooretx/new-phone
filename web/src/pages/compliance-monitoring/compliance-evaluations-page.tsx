import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { AlertTriangle, CheckCircle, XCircle, MinusCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { PageHeader } from "@/components/shared/page-header"
import {
  useComplianceEvaluations,
  useComplianceEvaluation,
  useTriggerComplianceEvaluation,
  useReviewComplianceEvaluation,
} from "@/api/compliance-monitoring"

function statusVariant(status: string) {
  switch (status) {
    case "completed":
      return "default"
    case "reviewed":
      return "secondary"
    case "failed":
      return "destructive"
    default:
      return "outline"
  }
}

function scoreVariant(score: number | null) {
  if (score == null) return "outline"
  if (score >= 80) return "default"
  if (score >= 60) return "secondary"
  return "destructive"
}

function resultIcon(result: string) {
  switch (result) {
    case "pass":
      return <CheckCircle className="h-4 w-4 text-green-600" />
    case "fail":
      return <XCircle className="h-4 w-4 text-red-600" />
    default:
      return <MinusCircle className="h-4 w-4 text-muted-foreground" />
  }
}

export function ComplianceEvaluationsPage() {
  const { t } = useTranslation()
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [flaggedFilter, setFlaggedFilter] = useState<boolean | undefined>(undefined)
  const { data: evaluations, isLoading } = useComplianceEvaluations({
    status: statusFilter || undefined,
    is_flagged: flaggedFilter,
  })
  const triggerEval = useTriggerComplianceEvaluation()
  const reviewEval = useReviewComplianceEvaluation()

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [triggerOpen, setTriggerOpen] = useState(false)
  const [triggerField, setTriggerField] = useState<"cdr" | "conversation">("conversation")
  const [triggerId, setTriggerId] = useState("")
  const [reviewNotes, setReviewNotes] = useState("")

  const { data: detail } = useComplianceEvaluation(selectedId || "")

  const handleTrigger = () => {
    const data =
      triggerField === "cdr"
        ? { cdr_id: triggerId }
        : { ai_conversation_id: triggerId }
    triggerEval.mutate(data, {
      onSuccess: () => {
        setTriggerOpen(false)
        setTriggerId("")
        toast.success(t("complianceMonitoring.evaluations.triggered"))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleReview = () => {
    if (!selectedId) return
    reviewEval.mutate(
      { evaluationId: selectedId, review_notes: reviewNotes || null },
      {
        onSuccess: () => {
          setReviewNotes("")
          toast.success(t("complianceMonitoring.evaluations.reviewed"))
        },
        onError: (err) => toast.error(err.message),
      }
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("complianceMonitoring.evaluations.title")}
        description={t("complianceMonitoring.evaluations.description")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Compliance" }, { label: t("complianceMonitoring.evaluations.title") }]}
      >
        <Button onClick={() => setTriggerOpen(true)}>
          {t("complianceMonitoring.evaluations.trigger")}
        </Button>
      </PageHeader>

      {/* Filters */}
      <div className="flex gap-4 items-center">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder={t("complianceMonitoring.evaluations.col.status")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">{t("common.all")}</SelectItem>
            <SelectItem value="pending">{t("complianceMonitoring.evaluations.status.pending")}</SelectItem>
            <SelectItem value="completed">{t("complianceMonitoring.evaluations.status.completed")}</SelectItem>
            <SelectItem value="failed">{t("complianceMonitoring.evaluations.status.failed")}</SelectItem>
            <SelectItem value="reviewed">{t("complianceMonitoring.evaluations.status.reviewed")}</SelectItem>
          </SelectContent>
        </Select>
        <Button
          variant={flaggedFilter === true ? "default" : "outline"}
          size="sm"
          onClick={() => setFlaggedFilter(flaggedFilter === true ? undefined : true)}
        >
          <AlertTriangle className="mr-1 h-3 w-3" />
          {t("complianceMonitoring.evaluations.col.flagged")}
        </Button>
      </div>

      {isLoading && <div className="text-muted-foreground">{t("common.loading")}</div>}

      {evaluations && evaluations.length === 0 && (
        <Card className="p-8 text-center text-muted-foreground">
          {t("complianceMonitoring.evaluations.noEvaluations")}
        </Card>
      )}

      {evaluations && evaluations.length > 0 && (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("complianceMonitoring.evaluations.col.evaluatedAt")}</TableHead>
                <TableHead>{t("complianceMonitoring.evaluations.col.score")}</TableHead>
                <TableHead>{t("complianceMonitoring.evaluations.col.flagged")}</TableHead>
                <TableHead>{t("complianceMonitoring.evaluations.col.status")}</TableHead>
                <TableHead>{t("complianceMonitoring.evaluations.col.rulesPassed")}</TableHead>
                <TableHead>{t("complianceMonitoring.evaluations.col.rulesFailed")}</TableHead>
                <TableHead>{t("complianceMonitoring.evaluations.col.provider")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {evaluations.map((ev) => (
                <TableRow
                  key={ev.id}
                  className="cursor-pointer"
                  onClick={() => setSelectedId(ev.id)}
                >
                  <TableCell>
                    {ev.evaluated_at
                      ? new Date(ev.evaluated_at).toLocaleString()
                      : "-"}
                  </TableCell>
                  <TableCell>
                    {ev.overall_score != null ? (
                      <Badge variant={scoreVariant(ev.overall_score)}>
                        {ev.overall_score.toFixed(0)}%
                      </Badge>
                    ) : (
                      "-"
                    )}
                  </TableCell>
                  <TableCell>
                    {ev.is_flagged && (
                      <AlertTriangle className="h-4 w-4 text-red-500" />
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusVariant(ev.status)}>
                      {t(`complianceMonitoring.evaluations.status.${ev.status}`, { defaultValue: ev.status })}
                    </Badge>
                  </TableCell>
                  <TableCell>{ev.rules_passed}</TableCell>
                  <TableCell>{ev.rules_failed}</TableCell>
                  <TableCell>{ev.provider_name || "-"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Detail dialog */}
      <Dialog open={!!selectedId} onOpenChange={() => setSelectedId(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t("complianceMonitoring.evaluations.detail")}</DialogTitle>
          </DialogHeader>
          {detail && (
            <div className="space-y-6">
              {/* Score summary */}
              <div className="flex gap-4 items-center">
                <Badge variant={scoreVariant(detail.overall_score)} className="text-lg px-3 py-1">
                  {detail.overall_score != null ? `${detail.overall_score.toFixed(0)}%` : "N/A"}
                </Badge>
                <Badge variant={statusVariant(detail.status)}>
                  {t(`complianceMonitoring.evaluations.status.${detail.status}`, { defaultValue: detail.status })}
                </Badge>
                {detail.is_flagged && (
                  <Badge variant="destructive">
                    <AlertTriangle className="mr-1 h-3 w-3" />
                    {t("complianceMonitoring.evaluations.col.flagged")}
                  </Badge>
                )}
              </div>

              {/* Rule results */}
              <div>
                <h3 className="font-medium mb-2">{t("complianceMonitoring.evaluations.ruleResults")}</h3>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-8" />
                      <TableHead>{t("complianceMonitoring.rules.form.name")}</TableHead>
                      <TableHead>{t("complianceMonitoring.evaluations.col.status")}</TableHead>
                      <TableHead>{t("complianceMonitoring.rules.form.description")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {detail.rule_results.map((rr) => (
                      <TableRow key={rr.id}>
                        <TableCell>{resultIcon(rr.result)}</TableCell>
                        <TableCell className="font-medium">{rr.rule_name_snapshot}</TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              rr.result === "pass"
                                ? "default"
                                : rr.result === "fail"
                                  ? "destructive"
                                  : "secondary"
                            }
                          >
                            {t(`complianceMonitoring.evaluations.result.${rr.result}`, { defaultValue: rr.result })}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm">
                          {rr.explanation}
                          {rr.evidence && (
                            <div className="mt-1 text-xs text-muted-foreground italic">
                              &ldquo;{rr.evidence}&rdquo;
                            </div>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Transcript */}
              <div>
                <h3 className="font-medium mb-2">{t("complianceMonitoring.evaluations.transcript")}</h3>
                <pre className="bg-muted p-4 rounded-md text-sm whitespace-pre-wrap max-h-64 overflow-y-auto">
                  {detail.transcript_text}
                </pre>
              </div>

              {/* Review form */}
              {detail.status !== "reviewed" && (
                <div className="space-y-2 border-t pt-4">
                  <h3 className="font-medium">{t("complianceMonitoring.evaluations.review")}</h3>
                  <Textarea
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    placeholder={t("complianceMonitoring.evaluations.reviewNotes")}
                    rows={3}
                  />
                  <Button onClick={handleReview} disabled={reviewEval.isPending}>
                    {reviewEval.isPending
                      ? t("common.saving")
                      : t("complianceMonitoring.evaluations.markReviewed")}
                  </Button>
                </div>
              )}

              {detail.review_notes && (
                <div className="border-t pt-4">
                  <h3 className="font-medium mb-1">{t("complianceMonitoring.evaluations.reviewNotes")}</h3>
                  <p className="text-sm text-muted-foreground">{detail.review_notes}</p>
                  {detail.reviewed_at && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {new Date(detail.reviewed_at).toLocaleString()}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Trigger dialog */}
      <Dialog open={triggerOpen} onOpenChange={setTriggerOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("complianceMonitoring.evaluations.trigger")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>{t("common.type")}</Label>
              <Select value={triggerField} onValueChange={(v) => setTriggerField(v as "cdr" | "conversation")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="cdr">{t("complianceMonitoring.evaluations.triggerCdr")}</SelectItem>
                  <SelectItem value="conversation">{t("complianceMonitoring.evaluations.triggerConversation")}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>
                {triggerField === "cdr"
                  ? t("complianceMonitoring.evaluations.triggerCdr")
                  : t("complianceMonitoring.evaluations.triggerConversation")}
              </Label>
              <Input
                value={triggerId}
                onChange={(e) => setTriggerId(e.target.value)}
                placeholder="UUID"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTriggerOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleTrigger} disabled={!triggerId.trim() || triggerEval.isPending}>
              {triggerEval.isPending ? t("common.saving") : t("complianceMonitoring.evaluations.trigger")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
