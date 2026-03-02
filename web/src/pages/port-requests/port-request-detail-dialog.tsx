import { useRef } from "react"
import { useTranslation } from "react-i18next"
import {
  usePortRequestHistory,
  useUploadLoa,
  useCheckPortStatus,
  useCancelPortRequest,
  useCompletePortRequest,
  type PortRequest,
  type PortRequestStatus,
} from "@/api/port-requests"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Loader2, Upload, RefreshCw, XCircle, CheckCircle2 } from "lucide-react"
import { toast } from "sonner"

const statusConfig: Record<PortRequestStatus, { label: string; variant: "default" | "secondary" | "outline" | "destructive" }> = {
  submitted: { label: "Submitted", variant: "default" },
  pending_loa: { label: "Pending LOA", variant: "secondary" },
  loa_submitted: { label: "LOA Submitted", variant: "secondary" },
  foc_received: { label: "FOC Received", variant: "default" },
  in_progress: { label: "In Progress", variant: "default" },
  completed: { label: "Completed", variant: "default" },
  rejected: { label: "Rejected", variant: "destructive" },
  cancelled: { label: "Cancelled", variant: "outline" },
}

const TERMINAL_STATUSES: PortRequestStatus[] = ["completed", "rejected", "cancelled"]

interface Props {
  portRequest: PortRequest | null
  onOpenChange: (open: boolean) => void
}

export function PortRequestDetailDialog({ portRequest, onOpenChange }: Props) {
  const { t } = useTranslation()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data: history, isLoading: historyLoading } = usePortRequestHistory(portRequest?.id ?? "")
  const uploadMutation = useUploadLoa()
  const checkStatusMutation = useCheckPortStatus()
  const cancelMutation = useCancelPortRequest()
  const completeMutation = useCompletePortRequest()

  const isTerminal = portRequest ? TERMINAL_STATUSES.includes(portRequest.status) : false

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !portRequest) return

    const maxSize = 10 * 1024 * 1024 // 10MB
    const allowedTypes = ["application/pdf", "image/png", "image/jpeg", "image/tiff"]
    if (file.size > maxSize) {
      toast.error(t("portRequests.loaFileTooLarge"))
      return
    }
    if (!allowedTypes.includes(file.type)) {
      toast.error(t("portRequests.loaInvalidType"))
      return
    }

    uploadMutation.mutate(
      { id: portRequest.id, file },
      {
        onSuccess: () => toast.success(t("portRequests.loaUploadSuccess")),
        onError: (err) => toast.error(err.message),
      }
    )
    // Reset input
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  const handleCheckStatus = () => {
    if (!portRequest) return
    checkStatusMutation.mutate(portRequest.id, {
      onSuccess: () => toast.success(t("portRequests.statusChecked")),
      onError: (err) => toast.error(err.message),
    })
  }

  const handleCancel = () => {
    if (!portRequest) return
    cancelMutation.mutate(portRequest.id, {
      onSuccess: () => {
        toast.success(t("portRequests.cancelSuccess"))
        onOpenChange(false)
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleComplete = () => {
    if (!portRequest) return
    completeMutation.mutate(portRequest.id, {
      onSuccess: () => {
        toast.success(t("portRequests.completeSuccess"))
        onOpenChange(false)
      },
      onError: (err) => toast.error(err.message),
    })
  }

  return (
    <Sheet open={!!portRequest} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{t("portRequests.detailTitle")}</SheetTitle>
        </SheetHeader>

        {portRequest && (
          <div className="mt-6 space-y-6">
            {/* Status */}
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">{t("portRequests.col.status")}</h4>
              <Badge variant={statusConfig[portRequest.status]?.variant ?? "outline"}>
                {statusConfig[portRequest.status]?.label ?? portRequest.status}
              </Badge>
            </div>

            {/* Numbers */}
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">{t("portRequests.col.numbers")}</h4>
              <div className="space-y-1">
                {portRequest.numbers.map((n) => (
                  <div key={n} className="font-mono text-sm">{n}</div>
                ))}
              </div>
            </div>

            {/* Details grid */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-1">{t("portRequests.col.carrier")}</h4>
                <p className="text-sm">{portRequest.current_carrier}</p>
              </div>
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-1">{t("portRequests.col.provider")}</h4>
                <p className="text-sm">{portRequest.provider}</p>
              </div>
              {portRequest.foc_date && (
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-1">{t("portRequests.col.focDate")}</h4>
                  <p className="text-sm">{new Date(portRequest.foc_date).toLocaleDateString()}</p>
                </div>
              )}
              {portRequest.requested_date && (
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-1">{t("portRequests.form.requestedDate")}</h4>
                  <p className="text-sm">{new Date(portRequest.requested_date).toLocaleDateString()}</p>
                </div>
              )}
            </div>

            {portRequest.notes && (
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-1">{t("portRequests.form.notes")}</h4>
                <p className="text-sm whitespace-pre-wrap">{portRequest.notes}</p>
              </div>
            )}

            {/* LOA Upload */}
            {!isTerminal && (
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-2">{t("portRequests.loaTitle")}</h4>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
                  className="hidden"
                  onChange={handleFileUpload}
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadMutation.isPending}
                >
                  {uploadMutation.isPending
                    ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    : <Upload className="mr-2 h-4 w-4" />}
                  {t("portRequests.loaUpload")}
                </Button>
                <p className="text-xs text-muted-foreground mt-1">{t("portRequests.loaHelp")}</p>
              </div>
            )}

            {/* Actions */}
            {!isTerminal && (
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" onClick={handleCheckStatus} disabled={checkStatusMutation.isPending}>
                  {checkStatusMutation.isPending
                    ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    : <RefreshCw className="mr-2 h-4 w-4" />}
                  {t("portRequests.checkStatus")}
                </Button>
                <Button variant="outline" size="sm" onClick={handleComplete} disabled={completeMutation.isPending}>
                  {completeMutation.isPending
                    ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    : <CheckCircle2 className="mr-2 h-4 w-4" />}
                  {t("portRequests.markComplete")}
                </Button>
                <Button variant="destructive" size="sm" onClick={handleCancel} disabled={cancelMutation.isPending}>
                  {cancelMutation.isPending
                    ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    : <XCircle className="mr-2 h-4 w-4" />}
                  {t("portRequests.cancelAction")}
                </Button>
              </div>
            )}

            {/* Timeline / History */}
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-3">{t("portRequests.historyTitle")}</h4>
              {historyLoading && (
                <div className="flex items-center justify-center h-16">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              )}
              {!historyLoading && history && history.length === 0 && (
                <p className="text-sm text-muted-foreground">{t("portRequests.noHistory")}</p>
              )}
              {!historyLoading && history && history.length > 0 && (
                <div className="relative border-l-2 border-muted pl-4 space-y-4">
                  {history.map((entry) => {
                    const cfg = statusConfig[entry.status] ?? { label: entry.status, variant: "outline" as const }
                    return (
                      <div key={entry.id} className="relative">
                        <div className="absolute -left-[1.35rem] top-1 h-2.5 w-2.5 rounded-full bg-primary" />
                        <div className="flex items-center gap-2 mb-0.5">
                          <Badge variant={cfg.variant} className="text-xs">{cfg.label}</Badge>
                          <span className="text-xs text-muted-foreground">
                            {new Date(entry.created_at).toLocaleString()}
                          </span>
                        </div>
                        {entry.message && (
                          <p className="text-sm text-muted-foreground">{entry.message}</p>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
