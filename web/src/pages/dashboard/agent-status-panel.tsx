import { useTranslation } from "react-i18next"
import { useAgentStatus } from "@/api/queues"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Users } from "lucide-react"

function statusBadgeVariant(status: string | null): "default" | "secondary" | "outline" {
  switch (status) {
    case "available":
      return "default"
    case "on_call":
    case "on_break":
      return "secondary"
    case "logged_out":
    default:
      return "outline"
  }
}

export function AgentStatusPanel() {
  const { t } = useTranslation()
  const { data: agents, isLoading } = useAgentStatus()

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-lg font-semibold">{t('dashboard.agentStatus')}</h2>
        </div>
        <Skeleton className="h-36" />
      </div>
    )
  }

  if (!agents || agents.length === 0) return null

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Users className="h-5 w-5 text-muted-foreground" />
        <h2 className="text-lg font-semibold">{t('dashboard.agentStatus')}</h2>
      </div>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">{t('dashboard.queueAgents')}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('dashboard.col.extension')}</TableHead>
                <TableHead>{t('dashboard.col.status')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {agents.map((agent) => (
                <TableRow key={agent.extension_id}>
                  <TableCell className="text-sm">{agent.extension_number}</TableCell>
                  <TableCell>
                    <Badge variant={statusBadgeVariant(agent.agent_status)}>
                      {agent.agent_status ?? t('common.unknown')}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
