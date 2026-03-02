import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Save } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { PageHeader } from "@/components/shared/page-header"
import { TimezoneSelect } from "@/components/shared/timezone-select"
import {
  useComplianceSettings,
  useUpdateComplianceSettings,
  type ComplianceSettingsUpdate,
} from "@/api/compliance"

export function ComplianceSettingsPage() {
  const { t } = useTranslation()
  const { data: settings, isLoading } = useComplianceSettings()
  const updateSettings = useUpdateComplianceSettings()

  const [windowStart, setWindowStart] = useState("08:00")
  const [windowEnd, setWindowEnd] = useState("21:00")
  const [timezone, setTimezone] = useState("America/New_York")
  const [enforceWindow, setEnforceWindow] = useState(true)
  const [syncSmsOptout, setSyncSmsOptout] = useState(false)
  const [autoDnc, setAutoDnc] = useState(true)
  const [nationalDnc, setNationalDnc] = useState(false)

  useEffect(() => {
    if (settings) {
      setWindowStart(settings.calling_window_start)
      setWindowEnd(settings.calling_window_end)
      setTimezone(settings.default_timezone)
      setEnforceWindow(settings.enforce_calling_window)
      setSyncSmsOptout(settings.sync_sms_optout_to_dnc)
      setAutoDnc(settings.auto_dnc_on_request)
      setNationalDnc(settings.national_dnc_enabled)
    }
  }, [settings])

  const handleSave = () => {
    const payload: ComplianceSettingsUpdate = {
      calling_window_start: windowStart,
      calling_window_end: windowEnd,
      default_timezone: timezone,
      enforce_calling_window: enforceWindow,
      sync_sms_optout_to_dnc: syncSmsOptout,
      auto_dnc_on_request: autoDnc,
      national_dnc_enabled: nationalDnc,
    }
    updateSettings.mutate(payload, {
      onSuccess: () => toast.success(t("compliance.settings.saved")),
      onError: (err) => toast.error(err.message),
    })
  }

  if (isLoading) {
    return <div className="text-muted-foreground p-6">{t("common.loading")}</div>
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("compliance.settings.title")}
        description={t("compliance.settings.description")}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Compliance", href: "/compliance/dnc-lists" }, { label: t("compliance.settings.title") }]}
      >
        <Button onClick={handleSave} disabled={updateSettings.isPending}>
          <Save className="mr-2 h-4 w-4" />
          {updateSettings.isPending ? t("common.saving") : t("common.save")}
        </Button>
      </PageHeader>

      <Card className="p-6 space-y-6">
        {/* Calling Window */}
        <div>
          <h3 className="text-lg font-semibold mb-4">{t("compliance.settings.callingWindow")}</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>{t("compliance.settings.windowStart")}</Label>
              <Input
                type="time"
                value={windowStart}
                onChange={(e) => setWindowStart(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>{t("compliance.settings.windowEnd")}</Label>
              <Input
                type="time"
                value={windowEnd}
                onChange={(e) => setWindowEnd(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>{t("compliance.settings.defaultTimezone")}</Label>
              <TimezoneSelect value={timezone} onChange={setTimezone} />
            </div>
          </div>
          <div className="flex items-center gap-3 mt-4">
            <Switch
              checked={enforceWindow}
              onCheckedChange={setEnforceWindow}
            />
            <Label>{t("compliance.settings.enforceCallingWindow")}</Label>
          </div>
        </div>

        <Separator />

        {/* Auto-DNC Settings */}
        <div>
          <h3 className="text-lg font-semibold mb-4">{t("compliance.settings.automation")}</h3>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Switch
                checked={syncSmsOptout}
                onCheckedChange={setSyncSmsOptout}
              />
              <div>
                <Label>{t("compliance.settings.syncSmsOptout")}</Label>
                <p className="text-sm text-muted-foreground">
                  {t("compliance.settings.syncSmsOptoutDesc")}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Switch
                checked={autoDnc}
                onCheckedChange={setAutoDnc}
              />
              <div>
                <Label>{t("compliance.settings.autoDnc")}</Label>
                <p className="text-sm text-muted-foreground">
                  {t("compliance.settings.autoDncDesc")}
                </p>
              </div>
            </div>
          </div>
        </div>

        <Separator />

        {/* National DNC */}
        <div>
          <h3 className="text-lg font-semibold mb-4">{t("compliance.settings.nationalDnc")}</h3>
          <div className="flex items-center gap-3">
            <Switch
              checked={nationalDnc}
              onCheckedChange={setNationalDnc}
            />
            <div>
              <Label>{t("compliance.settings.nationalDncEnabled")}</Label>
              <p className="text-sm text-muted-foreground">
                {t("compliance.settings.nationalDncDesc")}
              </p>
            </div>
          </div>
          {nationalDnc && (
            <div className="mt-3">
              <Badge variant="outline">{t("compliance.settings.nationalDncNotAvailable")}</Badge>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
