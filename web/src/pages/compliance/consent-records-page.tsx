import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Plus, Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
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
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import {
  useConsentRecords,
  useCreateConsentRecord,
  useRevokeConsent,
  type ConsentRecordCreate,
} from "@/api/compliance"

const CAMPAIGN_TYPES = [
  { value: "marketing", label: "Marketing" },
  { value: "transactional", label: "Transactional" },
  { value: "informational", label: "Informational" },
  { value: "political", label: "Political" },
  { value: "emergency", label: "Emergency" },
]

const CONSENT_METHODS = [
  { value: "web_form", label: "Web Form" },
  { value: "verbal", label: "Verbal" },
  { value: "paper", label: "Paper" },
  { value: "sms_keyword", label: "SMS Keyword" },
  { value: "api", label: "API" },
]

export function ConsentRecordsPage() {
  const { t } = useTranslation()
  const [phoneFilter, setPhoneFilter] = useState("")
  const [campaignFilter, setCampaignFilter] = useState("")
  const [activeFilter, setActiveFilter] = useState("")
  const [page, setPage] = useState(1)
  const [createOpen, setCreateOpen] = useState(false)
  const [revokeId, setRevokeId] = useState<string | null>(null)

  const { data, isLoading } = useConsentRecords({
    phone_number: phoneFilter || undefined,
    campaign_type: campaignFilter || undefined,
    is_active: activeFilter || undefined,
    page,
  })
  const createConsent = useCreateConsentRecord()
  const revokeConsent = useRevokeConsent()

  // Create form state
  const [formPhone, setFormPhone] = useState("")
  const [formCampaignType, setFormCampaignType] = useState("marketing")
  const [formConsentMethod, setFormConsentMethod] = useState("web_form")
  const [formConsentText, setFormConsentText] = useState("")

  const handleCreate = () => {
    const payload: ConsentRecordCreate = {
      phone_number: formPhone.trim(),
      campaign_type: formCampaignType,
      consent_method: formConsentMethod,
      consent_text: formConsentText || null,
    }
    createConsent.mutate(payload, {
      onSuccess: () => {
        setCreateOpen(false)
        setFormPhone("")
        setFormConsentText("")
        toast.success(t("compliance.consent.created"))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  const handleRevoke = () => {
    if (!revokeId) return
    revokeConsent.mutate(revokeId, {
      onSuccess: () => {
        setRevokeId(null)
        toast.success(t("compliance.consent.revoked"))
      },
      onError: (err) => toast.error(err.message),
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("compliance.consent.title")}
        description={t("compliance.consent.description")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Compliance", href: "/compliance/dnc-lists" }, { label: t("compliance.consent.title") }]}
      >
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          {t("compliance.consent.recordConsent")}
        </Button>
      </PageHeader>

      {/* Filters */}
      <div className="flex items-end gap-3">
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
          <Label className="text-xs">{t("compliance.consent.campaignType")}</Label>
          <Select value={campaignFilter} onValueChange={(v) => { setCampaignFilter(v === "all" ? "" : v); setPage(1) }}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder={t("common.all")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t("common.all")}</SelectItem>
              {CAMPAIGN_TYPES.map((ct) => (
                <SelectItem key={ct.value} value={ct.value}>{ct.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">{t("compliance.consent.status")}</Label>
          <Select value={activeFilter} onValueChange={(v) => { setActiveFilter(v === "all" ? "" : v); setPage(1) }}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder={t("common.all")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t("common.all")}</SelectItem>
              <SelectItem value="true">{t("compliance.consent.active")}</SelectItem>
              <SelectItem value="false">{t("compliance.consent.revokedStatus")}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {isLoading && <div className="text-muted-foreground">{t("common.loading")}</div>}

      {data && data.items.length === 0 && (
        <Card className="p-8 text-center text-muted-foreground">
          {t("compliance.consent.emptyTitle")}
        </Card>
      )}

      {data && data.items.length > 0 && (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("compliance.dnc.phoneNumber")}</TableHead>
                <TableHead>{t("compliance.consent.campaignType")}</TableHead>
                <TableHead>{t("compliance.consent.method")}</TableHead>
                <TableHead>{t("compliance.consent.consentedAt")}</TableHead>
                <TableHead>{t("compliance.consent.status")}</TableHead>
                <TableHead>{t("common.actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((record) => (
                <TableRow key={record.id}>
                  <TableCell className="font-mono">{record.phone_number}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{record.campaign_type}</Badge>
                  </TableCell>
                  <TableCell>{record.consent_method}</TableCell>
                  <TableCell>{new Date(record.consented_at).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <Badge variant={record.is_active ? "secondary" : "destructive"}>
                      {record.is_active
                        ? t("compliance.consent.active")
                        : t("compliance.consent.revokedStatus")}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {record.is_active && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setRevokeId(record.id)}
                      >
                        {t("compliance.consent.revoke")}
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
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

      {/* Create consent dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("compliance.consent.recordConsent")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>{t("compliance.dnc.phoneNumber")}</Label>
              <Input
                value={formPhone}
                onChange={(e) => setFormPhone(e.target.value)}
                placeholder="+15551234567"
              />
            </div>
            <div className="space-y-2">
              <Label>{t("compliance.consent.campaignType")}</Label>
              <Select value={formCampaignType} onValueChange={setFormCampaignType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CAMPAIGN_TYPES.map((ct) => (
                    <SelectItem key={ct.value} value={ct.value}>{ct.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>{t("compliance.consent.method")}</Label>
              <Select value={formConsentMethod} onValueChange={setFormConsentMethod}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CONSENT_METHODS.map((cm) => (
                    <SelectItem key={cm.value} value={cm.value}>{cm.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>{t("compliance.consent.consentText")}</Label>
              <Textarea
                value={formConsentText}
                onChange={(e) => setFormConsentText(e.target.value)}
                rows={3}
                placeholder={t("compliance.consent.consentTextPlaceholder")}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleCreate} disabled={!formPhone.trim() || createConsent.isPending}>
              {createConsent.isPending ? t("common.saving") : t("common.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Revoke confirmation */}
      <ConfirmDialog
        open={!!revokeId}
        onOpenChange={() => setRevokeId(null)}
        title={t("compliance.consent.revokeTitle")}
        description={t("compliance.consent.revokeConfirm")}
        confirmLabel={t("compliance.consent.revoke")}
        variant="destructive"
        onConfirm={handleRevoke}
      />
    </div>
  )
}
