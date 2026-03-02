import { useTranslation } from "react-i18next"
import { useQueueStats } from "@/api/queues"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Headphones } from "lucide-react"
import { cn } from "@/lib/utils"

export function QueueStatsPanel() {
  const { t } = useTranslation()
  const { data: stats, isLoading } = useQueueStats()

  if (isLoading) {
    return (
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">{t('dashboard.queueActivity')}</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-36" />
          <Skeleton className="h-36" />
        </div>
      </div>
    )
  }

  if (!stats || stats.length === 0) return null

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Headphones className="h-5 w-5 text-muted-foreground" />
        <h2 className="text-lg font-semibold">{t('dashboard.queueActivity')}</h2>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {stats.map((q) => {
          const critical = q.waiting_count > 0 && q.agents_available === 0
          return (
            <Card key={q.queue_id} className={cn(critical && "border-destructive")}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">{q.queue_name}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                  <span className="text-muted-foreground">{t('dashboard.waiting')}</span>
                  <span className="font-medium">{q.waiting_count}</span>
                  <span className="text-muted-foreground">{t('dashboard.available')}</span>
                  <span className="font-medium">{q.agents_available} / {q.agents_logged_in}</span>
                  <span className="text-muted-foreground">{t('dashboard.onCall')}</span>
                  <span className="font-medium">{q.agents_on_call}</span>
                </div>
                {q.longest_wait_seconds > 0 && (
                  <Badge variant={q.longest_wait_seconds > 60 ? "destructive" : "secondary"} className="text-xs">
                    {t('dashboard.longestWait')}: {q.longest_wait_seconds}s
                  </Badge>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
