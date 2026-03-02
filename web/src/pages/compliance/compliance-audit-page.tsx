import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Search, ChevronDown, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { PageHeader } from "@/components/shared/page-header"
import { useComplianceAuditLog } from "@/api/compliance"

const EVENT_TYPES = [
  { value: "dnc_check", label: "DNC Check" },
  { value: "dnc_add", label: "DNC Add" },
  { value: "dnc_remove", label: "DNC Remove" },
  { value: "consent_recorded", label: "Consent Recorded" },
  { value: "consent_revoked", label: "Consent Revoked" },
  { value: "bulk_upload", label: "Bulk Upload" },
  { value: "sms_sync", label: "SMS Sync" },
  { value: "settings_changed", label: "Settings Changed" },
  { value: "calling_window_blocked", label: "Calling Window Blocked" },
]

export function ComplianceAuditPage() {
  const { t } = useTranslation()
  const [eventFilter, setEventFilter] = useState("")
  const [phoneFilter, setPhoneFilter] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [page, setPage] = useState(1)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { data, isLoading } = useComplianceAuditLog({
    event_type: eventFilter || undefined,
    phone_number: phoneFilter || undefined,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
    page,
  })

  const eventBadgeVariant = (type: string): "default" | "secondary" | "destructive" | "outline" => {
    if (type.includes("remove") || type.includes("revoke") || type.includes("blocked")) return "destructive"
    if (type.includes("add") || type.includes("record") || type.includes("consent")) return "secondary"
    return "outline"
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("compliance.audit.title")}
        description={t("compliance.audit.description")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Compliance", href: "/compliance/dnc-lists" }, { label: t("compliance.audit.title") }]}
      />

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <Label className="text-xs">{t("compliance.audit.eventType")}</Label>
          <Select value={eventFilter} onValueChange={(v) => { setEventFilter(v === "all" ? "" : v); setPage(1) }}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder={t("common.all")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t("common.all")}</SelectItem>
              {EVENT_TYPES.map((et) => (
                <SelectItem key={et.value} value={et.value}>{et.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">{t("compliance.dnc.phoneNumber")}</Label>
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              value={phoneFilter}
              onChange={(e) => { setPhoneFilter(e.target.value); setPage(1) }}
              placeholder={t("compliance.dnc.phonePlaceholder")}
              className="pl-8 w-48"
            />
          </div>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">{t("compliance.audit.startDate")}</Label>
          <Input
            type="date"
            value={startDate}
            onChange={(e) => { setStartDate(e.target.value); setPage(1) }}
            className="w-40"
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">{t("compliance.audit.endDate")}</Label>
          <Input
            type="date"
            value={endDate}
            onChange={(e) => { setEndDate(e.target.value); setPage(1) }}
            className="w-40"
          />
        </div>
      </div>

      {isLoading && <div className="text-muted-foreground">{t("common.loading")}</div>}

      {data && data.items.length === 0 && (
        <Card className="p-8 text-center text-muted-foreground">
          {t("compliance.audit.emptyTitle")}
        </Card>
      )}

      {data && data.items.length > 0 && (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <TableHead>{t("compliance.audit.timestamp")}</TableHead>
                <TableHead>{t("compliance.audit.eventType")}</TableHead>
                <TableHead>{t("compliance.dnc.phoneNumber")}</TableHead>
                <TableHead>{t("compliance.audit.details")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((log) => (
                <>
                  <TableRow
                    key={log.id}
                    className="cursor-pointer"
                    onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}
                  >
                    <TableCell>
                      {expandedId === log.id
                        ? <ChevronDown className="h-4 w-4" />
                        : <ChevronRight className="h-4 w-4" />}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Badge variant={eventBadgeVariant(log.event_type)}>
                        {log.event_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono">
                      {log.phone_number || "-"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground truncate max-w-xs">
                      {log.details ? JSON.stringify(log.details).slice(0, 80) : "-"}
                    </TableCell>
                  </TableRow>
                  {expandedId === log.id && log.details && (
                    <TableRow key={`${log.id}-details`}>
                      <TableCell colSpan={5} className="bg-muted/50">
                        <pre className="text-xs overflow-auto p-2 max-h-48 whitespace-pre-wrap">
                          {JSON.stringify(log.details, null, 2)}
                        </pre>
                      </TableCell>
                    </TableRow>
                  )}
                </>
              ))}
            </TableBody>
          </Table>
          {data.total > data.per_page && (
            <div className="flex items-center justify-between p-4">
              <span className="text-sm text-muted-foreground">
                {t("compliance.pagination", {
                  from: (page - 1) * data.per_page + 1,
                  to: Math.min(page * data.per_page, data.total),
                  total: data.total,
                })}
              </span>
              <div className="flex gap-1">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                  {t("compliance.prev")}
                </Button>
                <Button variant="outline" size="sm" disabled={page * data.per_page >= data.total} onClick={() => setPage(page + 1)}>
                  {t("compliance.next")}
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
