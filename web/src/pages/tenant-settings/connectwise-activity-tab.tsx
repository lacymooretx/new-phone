import { useTranslation } from "react-i18next"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { TabsContent } from "@/components/ui/tabs"

interface CWTicketLog {
  id: string
  cw_ticket_id: number
  trigger_type: string
  ticket_summary: string
  status: string
  created_at: string
}

interface CWTicketLogStats {
  today: number
  this_week: number
  this_month: number
  total: number
}

interface ConnectWiseActivityTabProps {
  ticketLogs: CWTicketLog[] | undefined
  stats: CWTicketLogStats | undefined
}

export function ConnectWiseActivityTab({
  ticketLogs,
  stats,
}: ConnectWiseActivityTabProps) {
  const { t } = useTranslation()

  return (
    <TabsContent value="activity" className="space-y-4">
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <div className="rounded-lg border p-3 text-center">
            <p className="text-2xl font-bold">{stats.today}</p>
            <p className="text-xs text-muted-foreground">{t("connectwise.statsToday")}</p>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="text-2xl font-bold">{stats.this_week}</p>
            <p className="text-xs text-muted-foreground">{t("connectwise.statsWeek")}</p>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="text-2xl font-bold">{stats.this_month}</p>
            <p className="text-xs text-muted-foreground">{t("connectwise.statsMonth")}</p>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="text-2xl font-bold">{stats.total}</p>
            <p className="text-xs text-muted-foreground">{t("connectwise.statsTotal")}</p>
          </div>
        </div>
      )}

      {ticketLogs && ticketLogs.length > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("connectwise.ticketId")}</TableHead>
              <TableHead>{t("connectwise.trigger")}</TableHead>
              <TableHead>{t("connectwise.summary")}</TableHead>
              <TableHead>{t("connectwise.logStatus")}</TableHead>
              <TableHead>{t("connectwise.createdAt")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {ticketLogs.map((log) => (
              <TableRow key={log.id}>
                <TableCell className="font-mono">#{log.cw_ticket_id}</TableCell>
                <TableCell>
                  <Badge variant={log.trigger_type === "missed_call" ? "destructive" : "secondary"}>
                    {t(`connectwise.trigger_${log.trigger_type}`)}
                  </Badge>
                </TableCell>
                <TableCell className="max-w-xs truncate">{log.ticket_summary}</TableCell>
                <TableCell>
                  <Badge variant={log.status === "created" ? "default" : log.status === "failed" ? "destructive" : "secondary"}>
                    {log.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {new Date(log.created_at).toLocaleString()}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <p className="text-sm text-muted-foreground">{t("connectwise.noTicketLogs")}</p>
      )}
    </TabsContent>
  )
}
