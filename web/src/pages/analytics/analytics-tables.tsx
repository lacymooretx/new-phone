import { useTranslation } from "react-i18next"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  type ExtensionActivity,
  type DIDUsage,
  type TopCaller,
} from "@/api/analytics"

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${s.toString().padStart(2, "0")}`
}

interface AnalyticsTablesProps {
  extensions: ExtensionActivity[] | undefined
  extLoading: boolean
  dids: DIDUsage[] | undefined
  didsLoading: boolean
  callers: TopCaller[] | undefined
  callersLoading: boolean
}

export function AnalyticsTables({
  extensions,
  extLoading,
  dids,
  didsLoading,
  callers,
  callersLoading,
}: AnalyticsTablesProps) {
  const { t } = useTranslation()

  return (
    <>
      {/* Extension activity table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            {t("analytics.extensionActivity")}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {extLoading ? (
            <div className="p-6 space-y-2">
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
            </div>
          ) : extensions && extensions.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("analytics.extension")}</TableHead>
                  <TableHead>{t("analytics.name")}</TableHead>
                  <TableHead className="text-right">
                    {t("analytics.totalCalls")}
                  </TableHead>
                  <TableHead className="text-right">
                    {t("analytics.inbound")}
                  </TableHead>
                  <TableHead className="text-right">
                    {t("analytics.outbound")}
                  </TableHead>
                  <TableHead className="text-right">
                    {t("analytics.missed")}
                  </TableHead>
                  <TableHead className="text-right">
                    {t("analytics.avgDuration")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {extensions.map((ext) => (
                  <TableRow key={ext.extension_id}>
                    <TableCell className="font-mono text-sm">
                      {ext.extension_number}
                    </TableCell>
                    <TableCell className="text-sm">
                      {ext.extension_name ?? "\u2014"}
                    </TableCell>
                    <TableCell className="text-right">
                      {ext.total_calls}
                    </TableCell>
                    <TableCell className="text-right">{ext.inbound}</TableCell>
                    <TableCell className="text-right">{ext.outbound}</TableCell>
                    <TableCell className="text-right">{ext.missed}</TableCell>
                    <TableCell className="text-right">
                      {formatDuration(ext.avg_duration_seconds)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="p-6 text-sm text-muted-foreground text-center">
              {t("common.noResults")}
            </p>
          )}
        </CardContent>
      </Card>

      {/* DID usage table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            {t("analytics.didUsage")}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {didsLoading ? (
            <div className="p-6 space-y-2">
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
            </div>
          ) : dids && dids.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("analytics.didNumber")}</TableHead>
                  <TableHead className="text-right">
                    {t("analytics.totalCalls")}
                  </TableHead>
                  <TableHead className="text-right">
                    {t("analytics.answered")}
                  </TableHead>
                  <TableHead className="text-right">
                    {t("analytics.missed")}
                  </TableHead>
                  <TableHead className="text-right">
                    {t("analytics.avgDuration")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dids.map((did) => (
                  <TableRow key={did.did_id}>
                    <TableCell className="font-mono text-sm">
                      {did.number}
                    </TableCell>
                    <TableCell className="text-right">
                      {did.total_calls}
                    </TableCell>
                    <TableCell className="text-right">
                      {did.answered}
                    </TableCell>
                    <TableCell className="text-right">{did.missed}</TableCell>
                    <TableCell className="text-right">
                      {formatDuration(did.avg_duration_seconds)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="p-6 text-sm text-muted-foreground text-center">
              {t("common.noResults")}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Top callers table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            {t("analytics.topCallers")}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {callersLoading ? (
            <div className="p-6 space-y-2">
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
            </div>
          ) : callers && callers.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("analytics.callerNumber")}</TableHead>
                  <TableHead>{t("analytics.callerName")}</TableHead>
                  <TableHead className="text-right">
                    {t("analytics.totalCalls")}
                  </TableHead>
                  <TableHead className="text-right">
                    {t("analytics.totalDuration")}
                  </TableHead>
                  <TableHead className="text-right">
                    {t("analytics.avgDuration")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {callers.map((caller) => (
                  <TableRow key={caller.caller_number}>
                    <TableCell className="font-mono text-sm">
                      {caller.caller_number}
                    </TableCell>
                    <TableCell className="text-sm">
                      {caller.caller_name ?? "\u2014"}
                    </TableCell>
                    <TableCell className="text-right">
                      {caller.total_calls}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatDuration(caller.total_duration_seconds)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatDuration(caller.avg_duration_seconds)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="p-6 text-sm text-muted-foreground text-center">
              {t("common.noResults")}
            </p>
          )}
        </CardContent>
      </Card>
    </>
  )
}
