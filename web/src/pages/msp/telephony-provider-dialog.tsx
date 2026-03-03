import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import type { TelephonyProviderConfig, TelephonyProviderConfigCreate } from "@/api/telephony-providers"

interface TelephonyProviderFormData {
  provider_type: "clearlyip" | "twilio"
  label: string
  is_default: boolean
  notes: string
  // ClearlyIP
  base_url: string
  api_key: string
  // Twilio
  account_sid: string
  auth_token: string
}

const INITIAL_FORM: TelephonyProviderFormData = {
  provider_type: "clearlyip",
  label: "",
  is_default: false,
  notes: "",
  base_url: "",
  api_key: "",
  account_sid: "",
  auth_token: "",
}

function buildCredentials(form: TelephonyProviderFormData): Record<string, string> {
  if (form.provider_type === "clearlyip") {
    const creds: Record<string, string> = {}
    if (form.api_key) creds.api_key = form.api_key
    if (form.base_url) creds.base_url = form.base_url
    return creds
  }
  const creds: Record<string, string> = {}
  if (form.account_sid) creds.account_sid = form.account_sid
  if (form.auth_token) creds.auth_token = form.auth_token
  return creds
}

function editToFormData(config: TelephonyProviderConfig): TelephonyProviderFormData {
  return {
    provider_type: config.provider_type as "clearlyip" | "twilio",
    label: config.label,
    is_default: config.is_default,
    notes: config.notes || "",
    base_url: "",
    api_key: "",
    account_sid: "",
    auth_token: "",
  }
}

export function TelephonyProviderDialog({
  open,
  onOpenChange,
  editing,
  isLoading,
  onSubmit,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  editing: TelephonyProviderConfig | null
  isLoading: boolean
  onSubmit: (payload: TelephonyProviderConfigCreate, id?: string) => void
}) {
  const { t } = useTranslation()
  const [form, setForm] = useState<TelephonyProviderFormData>(
    editing ? editToFormData(editing) : INITIAL_FORM,
  )

  // Reset form when dialog opens
  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) {
      setForm(editing ? editToFormData(editing) : INITIAL_FORM)
    }
    onOpenChange(nextOpen)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const creds = buildCredentials(form)
    const payload: TelephonyProviderConfigCreate = {
      provider_type: form.provider_type,
      label: form.label,
      credentials: creds,
      is_default: form.is_default,
      notes: form.notes || undefined,
    }
    onSubmit(payload, editing?.id)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg" onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle>
            {editing
              ? t("telephonyProviders.edit")
              : t("telephonyProviders.create")}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>{t("telephonyProviders.form.provider")}</Label>
            <Select
              value={form.provider_type}
              onValueChange={(val) =>
                setForm({ ...form, provider_type: val as "clearlyip" | "twilio" })
              }
              disabled={!!editing}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="clearlyip">
                  {t("telephonyProviders.form.clearlyIP")}
                </SelectItem>
                <SelectItem value="twilio">
                  {t("telephonyProviders.form.twilio")}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>{t("telephonyProviders.form.label")}</Label>
            <Input
              value={form.label}
              onChange={(e) => setForm({ ...form, label: e.target.value })}
              placeholder={t("telephonyProviders.form.labelPlaceholder")}
              required
            />
          </div>

          {form.provider_type === "clearlyip" ? (
            <>
              <div className="space-y-2">
                <Label>{t("telephonyProviders.form.apiUrl")}</Label>
                <Input
                  value={form.base_url}
                  onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                  placeholder={t("telephonyProviders.form.apiUrlPlaceholder")}
                />
              </div>
              <div className="space-y-2">
                <Label>{t("telephonyProviders.form.apiKey")}</Label>
                <Input
                  value={form.api_key}
                  onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                  placeholder={t("telephonyProviders.form.apiKeyPlaceholder")}
                  type="password"
                />
              </div>
            </>
          ) : (
            <>
              <div className="space-y-2">
                <Label>{t("telephonyProviders.form.accountSid")}</Label>
                <Input
                  value={form.account_sid}
                  onChange={(e) => setForm({ ...form, account_sid: e.target.value })}
                  placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                />
              </div>
              <div className="space-y-2">
                <Label>{t("telephonyProviders.form.authToken")}</Label>
                <Input
                  value={form.auth_token}
                  onChange={(e) => setForm({ ...form, auth_token: e.target.value })}
                  placeholder={t("telephonyProviders.form.authTokenPlaceholder")}
                  type="password"
                />
              </div>
            </>
          )}

          <div className="flex items-center gap-2">
            <Switch
              checked={form.is_default}
              onCheckedChange={(checked) => setForm({ ...form, is_default: checked })}
            />
            <Label>{t("telephonyProviders.form.setDefault")}</Label>
          </div>

          <div className="space-y-2">
            <Label>{t("common.notes")}</Label>
            <Textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              placeholder={t("telephonyProviders.form.notesPlaceholder")}
              rows={2}
            />
          </div>

          <Button type="submit" disabled={isLoading} className="w-full">
            {isLoading ? t("common.saving") : t("common.save")}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
