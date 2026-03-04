import { useState } from "react"
import { PageHeader } from "@/components/shared/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { EmptyState } from "@/components/shared/empty-state"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { useCallbacks, useCancelCallback, type ScheduledCallback } from "@/api/callbacks"
import { toast } from "sonner"
import { Phone, XCircle, Clock, CheckCircle2, Loader2, AlertCircle } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

const statusConfig: Record<string, { icon: typeof Clock; color: string; label: string }> = {
  pending: { icon: Clock, color: "text-yellow-500", label: "Pending" },
  scheduled: { icon: Clock, color: "text-blue-500", label: "Scheduled" },
  in_progress: { icon: Phone, color: "text-green-500", label: "In Progress" },
  completed: { icon: CheckCircle2, color: "text-green-600", label: "Completed" },
  failed: { icon: AlertCircle, color: "text-red-500", label: "Failed" },
  cancelled: { icon: XCircle, color: "text-gray-400", label: "Cancelled" },
  expired: { icon: XCircle, color: "text-gray-400", label: "Expired" },
}

export function CallbacksPage() {
  const [statusFilter, setStatusFilter] = useState<string>("")
  const { data, isLoading } = useCallbacks(undefined, statusFilter || undefined)
  const cancelMutation = useCancelCallback()
  const [cancelTarget, setCancelTarget] = useState<ScheduledCallback | null>(null)

  const callbacks = data?.items ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Scheduled Callbacks"
        description="Virtual queue callbacks — callers who requested a callback instead of waiting on hold."
      />

      <div className="flex items-center gap-3">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All statuses</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="scheduled">Scheduled</SelectItem>
            <SelectItem value="in_progress">In Progress</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      ) : !callbacks.length ? (
        <EmptyState icon={Phone} title="No callbacks" description="No scheduled callbacks found." />
      ) : (
        <div className="space-y-3">
          {callbacks.map((cb) => {
            const cfg = statusConfig[cb.status] ?? statusConfig.pending
            const Icon = cfg.icon
            return (
              <Card key={cb.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Icon className={`h-5 w-5 ${cfg.color}`} />
                      <div>
                        <CardTitle className="text-base">
                          {cb.caller_name || cb.caller_number}
                        </CardTitle>
                        <p className="text-xs text-muted-foreground">{cb.caller_number}</p>
                      </div>
                      <Badge variant="outline">{cfg.label}</Badge>
                    </div>
                    {["pending", "scheduled"].includes(cb.status) && (
                      <Button variant="ghost" size="sm" onClick={() => setCancelTarget(cb)}>
                        <XCircle className="h-4 w-4 mr-1" />Cancel
                      </Button>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="pt-0 text-xs text-muted-foreground flex gap-4">
                  <span>Scheduled: {new Date(cb.scheduled_at).toLocaleString()}</span>
                  <span>Attempts: {cb.attempt_count}/{cb.max_attempts}</span>
                  {cb.agent_extension && <span>Agent: {cb.agent_extension}</span>}
                  {cb.notes && <span>Notes: {cb.notes}</span>}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <ConfirmDialog
        open={!!cancelTarget}
        onOpenChange={() => setCancelTarget(null)}
        title="Cancel Callback"
        description={`Cancel the callback for ${cancelTarget?.caller_name || cancelTarget?.caller_number}?`}
        onConfirm={async () => {
          if (cancelTarget) {
            await cancelMutation.mutateAsync(cancelTarget.id)
            toast.success("Callback cancelled")
            setCancelTarget(null)
          }
        }}
      />
    </div>
  )
}
