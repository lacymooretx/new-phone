import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Plus, CheckCircle, XCircle, CalendarOff } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

import { Textarea } from "@/components/ui/textarea"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { PageHeader } from "@/components/shared/page-header"
import { EmptyState } from "@/components/shared/empty-state"
import {
  useWfmTimeOffRequests,
  useCreateWfmTimeOffRequest,
  useReviewWfmTimeOffRequest,
  type WfmTimeOffRequest,
  type WfmTimeOffRequestCreate,
} from "@/api/workforce-management"

const STATUS_OPTIONS = [
  { value: "all", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "denied", label: "Denied" },
  { value: "cancelled", label: "Cancelled" },
] as const

function statusColor(status: string) {
  switch (status) {
    case "approved":
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
    case "denied":
      return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
    case "pending":
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
    default:
      return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200"
  }
}

const EMPTY_CREATE: WfmTimeOffRequestCreate = {
  extension_id: "",
  start_date: "",
  end_date: "",
  reason: "",
}

export function WfmTimeOffPage() {
  const { t } = useTranslation()
  const [statusFilter, setStatusFilter] = useState("all")

  // Queries
  const {
    data: requests,
    isLoading,
    isError,
    error,
  } = useWfmTimeOffRequests(
    statusFilter !== "all" ? { status: statusFilter } : undefined
  )

  // Mutations
  const createRequest = useCreateWfmTimeOffRequest()
  const reviewRequest = useReviewWfmTimeOffRequest()

  // Create dialog state
  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState<WfmTimeOffRequestCreate>(EMPTY_CREATE)

  // Review dialog state
  const [reviewOpen, setReviewOpen] = useState(false)
  const [reviewing, setReviewing] = useState<WfmTimeOffRequest | null>(null)
  const [reviewNotes, setReviewNotes] = useState("")

  // --- Handlers ---

  const openCreate = () => {
    setCreateForm(EMPTY_CREATE)
    setCreateOpen(true)
  }

  const handleCreate = () => {
    if (!createForm.extension_id.trim() || !createForm.start_date || !createForm.end_date) {
      toast.error(t("wfm.timeOff.validationError", "Extension, start date, and end date are required"))
      return
    }
    createRequest.mutate(createForm, {
      onSuccess: () => {
        setCreateOpen(false)
        setCreateForm(EMPTY_CREATE)
        toast.success(t("wfm.timeOff.created", "Time-off request submitted"))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const openReview = (req: WfmTimeOffRequest) => {
    setReviewing(req)
    setReviewNotes("")
    setReviewOpen(true)
  }

  const handleReview = (decision: "approved" | "denied") => {
    if (!reviewing) return
    reviewRequest.mutate(
      { id: reviewing.id, status: decision, review_notes: reviewNotes || null },
      {
        onSuccess: () => {
          setReviewOpen(false)
          setReviewing(null)
          toast.success(
            decision === "approved"
              ? t("wfm.timeOff.approved", "Request approved")
              : t("wfm.timeOff.denied", "Request denied")
          )
        },
        onError: (err) => toast.error(err.message),
      }
    )
  }

  const truncate = (text: string | null, max = 40) => {
    if (!text) return "-"
    return text.length > max ? `${text.slice(0, max)}...` : text
  }

  return (
    <div className="space-y-6">
      <PageHeader title={t("wfm.timeOff.title", "Time Off Requests")} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Workforce", href: "/wfm/shifts" }, { label: t("wfm.timeOff.title", "Time Off Requests") }]}>
        <Button onClick={openCreate}>
          <Plus className="mr-2 h-4 w-4" />
          {t("wfm.timeOff.newRequest", "New Request")}
        </Button>
      </PageHeader>

      {/* Status filter */}
      <div className="flex items-end gap-3">
        <div className="space-y-1">
          <Label className="text-xs">{t("wfm.timeOff.status", "Status")}</Label>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {t(`wfm.timeOff.status_${opt.value}`, opt.label)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Error */}
      {isError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t("common.failedToLoad", "Failed to load")}: {error?.message}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
          {t("common.loading", "Loading...")}
        </div>
      )}

      {/* Empty */}
      {!isLoading && (!requests || requests.length === 0) && (
        <EmptyState
          icon={CalendarOff}
          title={t("wfm.timeOff.emptyTitle", "No time-off requests")}
          description={t("wfm.timeOff.emptyDescription", "Submit a new request to get started.")}
          actionLabel={t("wfm.timeOff.newRequest", "New Request")}
          onAction={openCreate}
        />
      )}

      {/* Table */}
      {requests && requests.length > 0 && (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("wfm.timeOff.agent", "Agent")}</TableHead>
                <TableHead>{t("wfm.timeOff.startDate", "Start Date")}</TableHead>
                <TableHead>{t("wfm.timeOff.endDate", "End Date")}</TableHead>
                <TableHead>{t("wfm.timeOff.reason", "Reason")}</TableHead>
                <TableHead>{t("wfm.timeOff.status", "Status")}</TableHead>
                <TableHead>{t("wfm.timeOff.reviewedBy", "Reviewed By")}</TableHead>
                <TableHead className="w-24">{t("common.actions", "Actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {requests.map((req) => (
                <TableRow key={req.id}>
                  <TableCell className="font-medium">
                    {req.extension_name || req.extension_number}
                  </TableCell>
                  <TableCell>{req.start_date}</TableCell>
                  <TableCell>{req.end_date}</TableCell>
                  <TableCell className="max-w-[200px]" title={req.reason ?? undefined}>
                    {truncate(req.reason)}
                  </TableCell>
                  <TableCell>
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(req.status)}`}>
                      {req.status}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {req.reviewed_by_id ?? "-"}
                  </TableCell>
                  <TableCell>
                    {req.status === "pending" && (
                      <Button variant="outline" size="sm" onClick={() => openReview(req)}>
                        {t("wfm.timeOff.review", "Review")}
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{t("wfm.timeOff.createTitle", "New Time-Off Request")}</DialogTitle>
            <DialogDescription>
              {t("wfm.timeOff.createDescription", "Submit a time-off request for an agent.")}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>{t("wfm.timeOff.extensionId", "Extension ID")}</Label>
              <Input
                value={createForm.extension_id}
                onChange={(e) => setCreateForm((f) => ({ ...f, extension_id: e.target.value }))}
                placeholder="uuid..."
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>{t("wfm.timeOff.startDate", "Start Date")}</Label>
                <Input
                  type="date"
                  value={createForm.start_date}
                  onChange={(e) => setCreateForm((f) => ({ ...f, start_date: e.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label>{t("wfm.timeOff.endDate", "End Date")}</Label>
                <Input
                  type="date"
                  value={createForm.end_date}
                  onChange={(e) => setCreateForm((f) => ({ ...f, end_date: e.target.value }))}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>{t("wfm.timeOff.reason", "Reason")}</Label>
              <Textarea
                value={createForm.reason ?? ""}
                onChange={(e) => setCreateForm((f) => ({ ...f, reason: e.target.value }))}
                rows={3}
                placeholder={t("wfm.timeOff.reasonPlaceholder", "Vacation, sick leave, personal...")}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              {t("common.cancel", "Cancel")}
            </Button>
            <Button onClick={handleCreate} disabled={createRequest.isPending}>
              {createRequest.isPending
                ? t("common.saving", "Saving...")
                : t("wfm.timeOff.submit", "Submit Request")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Review Dialog */}
      <Dialog
        open={reviewOpen}
        onOpenChange={(open) => {
          if (!open) setReviewing(null)
          setReviewOpen(open)
        }}
      >
        <DialogContent onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>{t("wfm.timeOff.reviewTitle", "Review Request")}</DialogTitle>
            <DialogDescription>
              {t("wfm.timeOff.reviewDescription", "Approve or deny this time-off request.")}
            </DialogDescription>
          </DialogHeader>
          {reviewing && (
            <div className="space-y-4 py-2">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">{t("wfm.timeOff.agent", "Agent")}:</span>{" "}
                  <span className="font-medium">{reviewing.extension_name || reviewing.extension_number}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">{t("wfm.timeOff.status", "Status")}:</span>{" "}
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(reviewing.status)}`}>
                    {reviewing.status}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">{t("wfm.timeOff.startDate", "Start")}:</span>{" "}
                  {reviewing.start_date}
                </div>
                <div>
                  <span className="text-muted-foreground">{t("wfm.timeOff.endDate", "End")}:</span>{" "}
                  {reviewing.end_date}
                </div>
              </div>
              {reviewing.reason && (
                <div className="text-sm">
                  <span className="text-muted-foreground">{t("wfm.timeOff.reason", "Reason")}:</span>{" "}
                  {reviewing.reason}
                </div>
              )}
              <div className="space-y-2">
                <Label>{t("wfm.timeOff.reviewNotes", "Review Notes")}</Label>
                <Textarea
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  rows={3}
                  placeholder={t("wfm.timeOff.reviewNotesPlaceholder", "Optional notes...")}
                />
              </div>
            </div>
          )}
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setReviewOpen(false)}>
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              variant="destructive"
              onClick={() => handleReview("denied")}
              disabled={reviewRequest.isPending}
            >
              <XCircle className="mr-1 h-4 w-4" />
              {t("wfm.timeOff.deny", "Deny")}
            </Button>
            <Button
              onClick={() => handleReview("approved")}
              disabled={reviewRequest.isPending}
            >
              <CheckCircle className="mr-1 h-4 w-4" />
              {t("wfm.timeOff.approve", "Approve")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
